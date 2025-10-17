"""Module to create HipsGen images from a configuration file."""

import argparse
import re
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List

from yaml import safe_load

from utils import (
    create_config_file,
    extract_unique_id_from_filename,
    submit_slurm_job,
    create_config_by_band,
)


class HipsCreateByFileError(Exception):
    """Exceção personalizada para erros no HipsCreateByFile"""


class HipsCreateByFile:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.config = create_config_by_band(config)
        self.dryrun = config.get("dryrun", False)
        inputs = config.get("inputs", {})

        self.images_dir = Path(inputs.get("path_regex", "./inputs/*.fits"))

        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "images")
        self.output_dir.mkdir(exist_ok=True)

        # Patterns of bands
        band_patterns = inputs.get("pattern", None)
        if band_patterns and (
            "g" not in band_patterns
            or "r" not in band_patterns
            or "i" not in band_patterns
        ):
            print("Warning: Incomplete band patterns, using default patterns.")
            band_patterns = None

        # Find images organized by band
        self.images_by_band = self.find_fits_images(band_patterns)

        # Verify if found images
        total_images = sum(len(images) for images in self.images_by_band.values())
        if total_images == 0:
            raise HipsCreateByFileError("No fits images found!")

        # Limit number of images if specified
        if inputs.get("max_images", None):
            for band, images in self.images_by_band.items():
                if images and len(images) > inputs["max_images"]:
                    images = images[: inputs["max_images"]]
                    print(
                        f"Band {band}: processing only the first {inputs['max_images']} images"
                    )

        self.__jobs_submitted = {"g": [], "r": [], "i": []}

    def jobs_submitted(self, band: str = None) -> Dict[str, List[Dict]]:
        """Return the submitted jobs, optionally filtered by band"""
        if band:
            return {band: self.__jobs_submitted.get(band, [])}
        return self.__jobs_submitted

    def find_fits_images(
        self, band_patterns: Dict[str, str] = None
    ) -> Dict[str, List[Path]]:
        """
        Finds FITS images in the input directory and organizes them by band

        Args:
            band_patterns: Optional dict with regex patterns for each band

        Returns:
            Dict with lists of Paths for each band {band: [Path, ...]}
        """
        if band_patterns is None:
            # Patterns to identify bands in filenames
            band_patterns = {
                "g": r".*/g/.*[0-9].fits$",
                "r": r".*/r/.*[0-9].fits$",
                "i": r".*/i/.*[0-9].fits$",
            }

        # Find all FITS files
        all_fits = glob(str(self.images_dir), recursive=True)
        all_fits = [Path(f) for f in sorted(all_fits)]

        # Organize per band
        images_by_band = {"g": [], "r": [], "i": []}
        unmatched = []

        for fits_file in all_fits:
            filename = str(fits_file)
            matched = False

            for band, pattern_regex in band_patterns.items():
                print(f"Matching {filename} against pattern {pattern_regex}")
                if re.match(pattern_regex, filename, re.IGNORECASE):
                    images_by_band[band].append(fits_file)
                    matched = True
                    break

            if not matched:
                unmatched.append(fits_file)

        # Summary
        for band in ["g", "r", "i"]:
            print(f"  Band {band}: {len(images_by_band[band])} images")
            for img in images_by_band[band][:5]:  # Mostra primeiras 5
                print(f"    {img}")

        if unmatched:
            print(f"  Unmatched: {len(unmatched)}")
            for img in unmatched[:3]:
                print(f"    {img}")
            if len(unmatched) > 3:
                print(f"    ... and more {len(unmatched) - 3}")

        return images_by_band

    def submit_jobs(self):
        """Submit jobs to SLURM for each band and image"""

        jobs_submitted = self.jobs_submitted()
        if jobs_submitted:
            for jobs in jobs_submitted.values():
                if jobs:
                    print("Warning: Jobs already submitted, skipping.")
                    return

        for band, images in self.images_by_band.items():
            if not images:
                print(f"\nSkipping band {band}: no images found.")
                continue

            config = self.config.get(band, None)
            if not config:
                print(f"\nSkipping band {band}: no configuration found.")
                continue

            print(f"\nProcessing band {band} with {len(images)} images...")

            band_output_dir = self.output_dir / band
            band_output_dir.mkdir(exist_ok=True)

            for image_file in images:
                image_id = extract_unique_id_from_filename(image_file)
                img_output_dir = band_output_dir / image_id
                img_output_dir.mkdir(exist_ok=True)

                config_file = create_config_file(config, image_file, img_output_dir)

                # Register output for this image
                image_output = img_output_dir / "hips"
                image_output.mkdir(exist_ok=True)

                if self.dryrun:
                    print(
                        f"DRY RUN: would submit job for image {image_id} (band {band})"
                    )
                    job_id = f"job_{image_id}"
                else:
                    # Submit job to SLURM
                    job_id = submit_slurm_job(
                        sbatch_script="color.sbatch",
                        config_file=str(config_file.absolute()),
                        work_dir=str(img_output_dir.absolute()),
                        aladin_jar=self.alladin_cmd,
                        max_mem=self.max_mem,
                    )
                    print(f"Submitted job {job_id} for image {image_id} (band {band})")

                jobs = self.__jobs_submitted[band]
                jobs.append(
                    {
                        "id": job_id,
                        "output": str(image_output.absolute()),
                    }
                )

            for job in jobs:
                print(f"  Job: {job}")

        return self.jobs_submitted()


def main():
    """Main function to parse arguments and run HipsGen processing"""
    parser = argparse.ArgumentParser(
        description="Create HipsGen images from config file"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        required=True,
        help="Path to the YAML configuration file",
    )
    args = parser.parse_args()
    hipsimage = HipsCreateByFile(args.config)

    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsimage.max_mem}g -jar {hipsimage.alladin_cmd}"
    )
    print(f"Working directory: {hipsimage.output_dir}")

    hipsimage.submit_jobs()


if __name__ == "__main__":
    sys.exit(main())
