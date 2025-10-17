"""Module to create HipsGen images from a configuration file."""

import argparse
import re
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List, Optional

from yaml import safe_load

from utils import (
    prepare_sbatch_cmd,
    create_config_file,
    create_rgb_config,
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

        self.rgb_config = create_rgb_config(config)
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

        # Find images organized: {}
        self.images = self.find_fits_images(band_patterns)

        # Verify if found images
        total_images = sum(len(images) for images in self.images.values())
        if total_images == 0:
            raise HipsCreateByFileError("No fits images found!")

        # Limit number of images if specified
        if inputs.get("max_images", None):
            img_names = list(self.images.keys())
            print(f"Total images found: {len(img_names)}")
            print(f"{img_names}")
            max_imgs = img_names[: inputs["max_images"]]
            for images in img_names:
                if not images in max_imgs:
                    self.images.pop(images)
            print(f"Processing only the first {inputs['max_images']} images")

        self.__jobs_submitted = []

    @property
    def jobs_submitted(self) -> Dict[str, List[Dict]]:
        """Return the submitted jobs"""
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
        images = {}
        unmatched = []

        for fits_file in all_fits:
            filepath = str(fits_file)
            filename = str(fits_file.name)
            matched = False

            for band, pattern_regex in band_patterns.items():
                print(f"Matching {filepath} against pattern {pattern_regex}")
                if re.match(f".*{pattern_regex}.*.fits$", filename, re.IGNORECASE):
                    key = filename.replace(".fits", "").replace(pattern_regex, "")
                    if key not in images:
                        images[key] = {}
                    images[key][band] = str(fits_file)
                    matched = True
                    break

            if not matched:
                unmatched.append(fits_file)

        # Summary
        for key, value in images.items():
            print("--------------------")
            print(f"  Image {key}")
            for band, img in value.items():
                print(f"    {band}: {img}")
            print("--------------------\n")

        if unmatched:
            print(f"  Unmatched: {len(unmatched)}")
            for img in unmatched[:3]:
                print(f"    {img}")
            if len(unmatched) > 3:
                print(f"    ... and more {len(unmatched) - 3}")

        return images

    def submit_jobs(self):
        """Submit jobs to SLURM for each band and image"""

        for image_id, images in self.images.items():
            if not images:
                print(f"\nSkipping image {image_id}: no images found.")
                continue

            image = self.submit_by_image(image_id, images)
            jobs = image["jobs"]
            img_output_dir = image["img_output_dir"]

            print("\n---------------------------")
            print(f"Submitted jobs for image {image_id}:")
            for band, job in jobs.items():
                print(f"  Band {band}: {job}")
            print("---------------------------\n")

            job_consolidate = self.submit_consolidate_rgb(
                image_id, img_output_dir, jobs
            )
            print(f"Submitted RGB consolidate job: {job_consolidate}")

            self.__jobs_submitted.append(job_consolidate)
        return self.jobs_submitted

    def submit_consolidate_rgb(
        self, image_id: str, img_output_dir: str, jobs: Dict[str, Dict]
    ) -> Dict:
        """Submit a SLURM job to consolidate RGB images

        Args:
            image_id: Unique identifier for the image
            img_output_dir: Output directory for the image
            jobs: Dict with band as key and job info as value

        Returns:
            Job info dict for the consolidate job
        """

        rgb_output_dir = Path(img_output_dir) / "rgb"
        rgb_output_dir.mkdir(exist_ok=True)

        dependency_ids = [jobs[band]["id"] for band in ["g", "r", "i"] if band in jobs]

        if len(dependency_ids) < 3:
            raise HipsCreateByFileError(
                f"Cannot submit RGB consolidate job for image {image_id}: missing band jobs."
            )

        rgb_config = self.rgb_config.copy()
        rgb_config = self.update_rgb_config_input_paths(rgb_config, jobs)

        config_file = create_config_file(rgb_config, rgb_output_dir)
        cmd = prepare_sbatch_cmd(
            "rgb.sbatch",
            config_file=str(config_file),
            aladin_jar=self.alladin_cmd,
            max_mem=self.max_mem,
            dependency=":".join(map(str, dependency_ids)),
        )
        cmd.append(str(rgb_output_dir))

        print(f"Submitting RGB consolidate job with command: {' '.join(cmd)}")

        if self.dryrun:
            job_id = f"rgb.{image_id}"
            print("DRY RUN: would submit RGB consolidate job")
        else:
            job_id = submit_slurm_job(
                cmd,
                work_dir=str(self.output_dir.absolute()),
            )
            print(f"Submitted RGB consolidate job {job_id}")

        return {
            "id": job_id,
            "output_dir": str(rgb_output_dir),
            "slurm_job_dependencies": dependency_ids,
        }

    def update_rgb_config_input_paths(
        self, rgb_config: Dict, jobs: Dict[str, Dict]
    ) -> Dict:
        """Update RGB config input paths based on submitted jobs

        Args:
            rgb_config: Base RGB configuration dictionary
            jobs: Dict with band as key and job info as value

        Returns:
            Updated RGB configuration dictionary
        """

        mapping_colors = {
            "r": "inRed",
            "g": "inBlue",
            "i": "inGreen",
        }

        for band, color in mapping_colors.items():
            job_info = jobs.get(band, None)
            if job_info:
                rgb_config[color] = job_info.get("output_dir")
            else:
                raise HipsCreateByFileError(f"No job info found for band {band}!")

        return rgb_config

    def submit_by_image(self, image_id: str, images: Dict[str, str]) -> None:
        """Submit jobs to SLURM for each image

        Args:
            image_id: Unique identifier for the image
            images: Dict with band as key and image path as value

        Returns:
            Dict with band as key and job info as value
        """

        img_output_dir = self.output_dir / image_id
        img_output_dir.mkdir(exist_ok=True)

        image_jobs = {}

        for band in images.keys():
            config = self.config.get(band, None)

            if not config:
                print(f"\nSkipping band {band}: no configuration found.")
                raise HipsCreateByFileError(f"No configuration for band {band}!")

            band_output_dir = img_output_dir / band
            band_output_dir.mkdir(exist_ok=True)

            config["input"] = images[band]
            config_file = create_config_file(config, band_output_dir)

            cmd = prepare_sbatch_cmd(
                "color.sbatch",
                config_file=config_file,
                aladin_jar=self.alladin_cmd,
                max_mem=self.max_mem,
            )
            print(
                f"Submitting job for image {image_id} (band {band}) with command: {' '.join(cmd)}"
            )

            if self.dryrun:
                job_id = f"{band}.{image_id}"
                print(f"DRY RUN: would submit job for image {image_id} (band {band})")
            else:
                # Submit job to SLURM
                job_id = submit_slurm_job(cmd, str(img_output_dir.absolute()))
                print(f"Submitted job {job_id} for image {image_id} (band {band})")

            image_jobs[band] = {"id": job_id, "output_dir": str(band_output_dir)}

        return {
            "image_id": image_id,
            "jobs": image_jobs,
            "img_output_dir": str(img_output_dir),
        }


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

    print("/n/nSubmitting jobs...")
    jobs = hipsimage.submit_jobs()

    print(f"Total jobs submitted: {len(jobs)}")
    for job in jobs:
        print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
