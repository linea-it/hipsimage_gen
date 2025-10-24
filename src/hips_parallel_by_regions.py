"""Module to create HipsGen by regions from a configuration file."""

import argparse
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List

from yaml import safe_load

from utils import (
    prepare_sbatch_cmd,
    create_config_file,
    submit_slurm_job,
    create_config_by_band,
    create_rgb_config,
)


class HipsParallelByRegionsError(Exception):
    """Except for errors in HipsParallelByRegions"""


class HipsParallelByRegions:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict, index_path: str) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.rgb_config = create_rgb_config(config)
        self.config = create_config_by_band(config)
        self.dryrun = config.get("dryrun", False)
        self.creator_did = config.get("hipsgen", {}).pop("creator_did", "CDS/P/HIPS")

        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "bands")
        self.output_dir.mkdir(exist_ok=True)
        self.regions, self.npixs_count = self.__get_regions(index_path)

        self.mapping_colors = {
            "i": "red",
            "g": "blue",
            "r": "green",
        }

        self.__jobs_submitted = []

    @property
    def jobs_submitted(self) -> Dict[str, List[Dict]]:
        """Return the submitted jobs"""
        return self.__jobs_submitted

    def __get_regions(self, index_path: str):
        """ """
        ndirs = glob(f"{index_path}/HpxFinder/Norder*/Dir*")
        regions = []
        npixs_count = []

        for d in ndirs:
            ndir = Path(d)
            norder = int(ndir.parent.name.replace("Norder", ""))
            npixs = self.__get_min_max_by_dir(ndir)

            if not npixs:
                raise HipsParallelByRegionsError("Npixs not found!")

            if len(npixs) == 1:
                regions.append(f"{norder}/{npixs[0]}")
            else:
                regions.append(f"{norder}/{npixs[0]}-{npixs[1]}")
            npixs_count.append(npixs[2])

        return regions, npixs_count

    def __get_min_max_by_dir(self, dir_path: Path):
        """Get min and max Npixs by directory"""

        npixs = sorted(glob(str(dir_path / "Npix*")))
        npix_count = len(npixs)

        _min = int(Path(npixs[0]).name.replace("Npix", ""))
        _max = int(Path(npixs[-1]).name.replace("Npix", ""))
        npixs = sorted(list(set([_min, _max])))
        npixs.append(npix_count)
        return npixs

    def submit_by_region(self, region: str, npix_count: int) -> None:
        """Submit jobs to SLURM for each region

        Args:
            region: Unique identifier for the region

        Returns:
            Dict with band as key and job info as value
        """

        region_id = region.replace("/", ".")

        region_output_dir = self.output_dir / f"{region_id}.{str(npix_count)}"
        region_output_dir.mkdir(exist_ok=True)

        jobs = {}

        for band in self.mapping_colors:
            config = self.config.get(band, None)
            config["region"] = region

            if not config:
                print(f"\nSkipping band {band}: no configuration found.")
                raise HipsParallelByRegionsError(f"No configuration for band {band}!")

            band_output_dir = region_output_dir / band
            band_output_dir.mkdir(exist_ok=True)

            config["out"] = str(band_output_dir)
            config["creator_did"] = f"{self.creator_did}/{region_id.replace('.', '_')}"

            config_file = create_config_file(config, str(band_output_dir / "config"))

            cmd = prepare_sbatch_cmd(
                "png.sbatch",
                config_file=config_file,
                aladin_jar=self.alladin_cmd,
                max_mem=self.max_mem,
            )
            print(
                f"Submitting job for image {region_id} (band {band}) with command: {' '.join(cmd)}"
            )

            if self.dryrun:
                job_id = f"{band}.{region_id}"
                print(f"DRY RUN: would submit job for region {region_id} (band {band})")
            else:
                # Submit job to SLURM
                job_id = submit_slurm_job(cmd, str(region_output_dir.absolute()))
                print(f"Submitted job {job_id} for image {region_id} (band {band})")

            jobs[band] = {"id": job_id, "output_dir": str(band_output_dir)}

        return {
            "region_id": region_id,
            "jobs": jobs,
            "output_dir": str(region_output_dir),
        }

    def submit_jobs(self):
        """Submit jobs to SLURM for each band and image"""

        for idx, region in enumerate(self.regions):
            npix_count = self.npixs_count[idx]
            job = self.submit_by_region(region, npix_count)
            region_id = job["region_id"]
            jobs = job["jobs"]
            region_output_dir = job["output_dir"]

            job_consolidate = self.submit_consolidate_rgb(
                region_id, region_output_dir, jobs
            )
            print(f"Submitted jobs by region {region}: {job_consolidate}")

            self.__jobs_submitted.append(job_consolidate)
        return self.jobs_submitted

    def submit_consolidate_rgb(
        self, region_id: str, region_output_dir: str, jobs: Dict[str, Dict]
    ) -> Dict:
        """Submit a SLURM job to consolidate RGB regions

        Args:
            region_id: Unique identifier for the region
            img_output_dir: Output directory for the region
            jobs: Dict with band as key and job info a region

        Returns:
            Job info dict for the consolidate job
        """

        rgb_output_dir = Path(region_output_dir) / "rgb"
        rgb_output_dir.mkdir(exist_ok=True)

        dependency_ids = [jobs[band]["id"] for band in ["g", "r", "i"] if band in jobs]

        if len(dependency_ids) < 3:
            raise HipsParallelByRegionsError(
                f"Cannot submit RGB consolidate job for region {region_id}: missing band jobs."
            )

        rgb_config = self.rgb_config.copy()
        rgb_config = self.update_rgb_config_input_paths(rgb_config, jobs)
        rgb_config["out"] = str(rgb_output_dir)
        rgb_config["creator_did"] = f"{self.creator_did}/{region_id.replace('.', '_')}"

        config_file = create_config_file(rgb_config, str(rgb_output_dir / "config"))
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
            job_id = f"rgb.{region_id}"
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

        for band, color in self.mapping_colors.items():
            job_info = jobs.get(band, None)
            if job_info:
                color = color.capitalize()
                rgb_config[f"in{color}"] = job_info.get("output_dir")
            else:
                raise HipsParallelByRegionsError(f"No job info found for band {band}!")

        return rgb_config


def main():
    """Main function to parse arguments and run HipsGen processing"""

    from hips_create_index import HipsCreateIndex

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

    # hipsindex = HipsCreateIndex(args.config)
    # job = hipsindex.submit()
    # index_path = job["output_dir"]

    index_path = "/mnt/EXT4/hips/dc2/test02/index/"

    hipsimage = HipsParallelByRegions(args.config, index_path)

    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsimage.max_mem}g -jar {hipsimage.alladin_cmd}"
    )
    print(f"Working directory: {hipsimage.output_dir}")

    print("\n\nSubmitting jobs...")
    jobs = hipsimage.submit_jobs()

    print(f"Total jobs submitted: {len(jobs)}")
    for job in jobs:
        print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
