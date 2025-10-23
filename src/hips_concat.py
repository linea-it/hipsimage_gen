#!/usr/bin/env python3
""" """

import argparse
import shutil
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List, Tuple

from yaml import safe_load

from utils import (
    prepare_sbatch_cmd,
    create_concat_config,
    group_into_pairs,
    submit_slurm_job,
    create_config_file,
)


class HipsConcatError(Exception):
    """ """


class HipsConcat:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict, jobs: List[Dict]) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.config = create_concat_config(config)
        self.dryrun = config.get("dryrun", False)
        config.pop("inputs", None)

        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "concat")
        self.output_dir.mkdir(exist_ok=True)

        self.__jobs = self.__sorted_jobs(jobs)
        self.__main_job = self.__prepare_main_job(
            self.__jobs.pop(-1)
        )  # returns the largest job

    @property
    def jobs(self) -> List[Dict]:
        """Return the submitted jobs"""
        return self.__jobs

    @property
    def main_job(self) -> Dict:
        """Return the main job"""
        return self.__main_job

    def __prepare_main_job(self, job: Dict):
        """Prepare main job"""

        job_output = Path(job["output_dir"])
        if not job_output.exists():
            raise HipsConcatError(f"Output directory {job_output} does not exist!")

        job_output = shutil.copytree(job_output, self.output_dir)
        job["output_dir"] = str(job_output)
        return job

    def __sorted_jobs(self, jobs: List[Dict]):
        """Sort jobs by npixs"""

        for job in jobs:
            npixs = int(Path(job.get("output_dir")).parent.name.split(".")[-1])
            job["npixs"] = npixs
            job.pop("slurm_job_dependencies", None)

        return sorted(jobs, key=lambda x: x["npixs"])

    def make_concat_jobs(self):
        """Make concat jobs"""

        submitted_jobs = []

        for job in self.jobs:
            config_concat = self.config.copy()
            config_concat["in"] = job.get("output_dir")
            config_concat["out"] = self.main_job.get("output_dir")

            config_file = create_config_file(
                config_concat,
                str(self.output_dir / f"{job.get('id')}.config"),
            )

            dependencies = [
                job.get("id"),
                self.main_job.get("id"),
            ]

            dep_str = ":".join(map(str, dependencies))
            cmd = prepare_sbatch_cmd(
                "concat.sbatch",
                config_file=str(config_file),
                aladin_jar=self.alladin_cmd,
                max_mem=self.max_mem,
                dependency=dep_str,
            )

            print(f"Submitting concat job with command: {' '.join(cmd)}")

            if self.dryrun:
                job_id = f"concat-{dep_str.replace(':', '.')}"
                print(f"DRY RUN: would submit concat job {job_id}")
            else:
                job_id = submit_slurm_job(
                    cmd,
                    work_dir=str(self.output_dir.parent.absolute()),
                )
                print(f"Submitted concat job {job_id}")

            job = {
                "id": job_id,
                "output_dir": self.main_job.get("output_dir"),
                "slurm_job_dependencies": dependencies,
            }

            submitted_jobs.append(job)

        return submitted_jobs


def main():
    """Main function to parse arguments and run HipsGen processing"""

    from hips_create_index import HipsCreateIndex
    from hips_parallel_by_regions import HipsParallelByRegions

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

    # hipsimage = HipsParallelByRegions(args.config, job)
    # jobs = hipsimage.submit_jobs()

    jobs = [
        {
            "id": 22856,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141328351-141328383.32/rgb",
            "npixs": 32,
        },
        {
            "id": 22860,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141492224-141492226.2/rgb",
            "npixs": 2,
        },
        {
            "id": 22864,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141360000-141369007.9007/rgb",
            "npixs": 9007,
        },
        {
            "id": 22868,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141386402-141388546.2144/rgb",
            "npixs": 2144,
        },
        {
            "id": 22872,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141348831-141349887.1056/rgb",
            "npixs": 1056,
        },
        {
            "id": 22876,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141447248-141448962.1714/rgb",
            "npixs": 1714,
        },
        {
            "id": 22880,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141400064-141406210.6146/rgb",
            "npixs": 6146,
        },
        {
            "id": 22884,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141350111-141359999.9888/rgb",
            "npixs": 9888,
        },
        {
            "id": 22888,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141370335-141377535.7200/rgb",
            "npixs": 7200,
        },
        {
            "id": 22892,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141393920-141399810.5890/rgb",
            "npixs": 5890,
        },
        {
            "id": 22896,
            "output_dir": "/scratch/users/singulani/hipsimage_gen/outputs/bands/12.141410304-141410306.2/rgb",
            "npixs": 2,
        },
    ]

    hipsconcat = HipsConcat(args.config, jobs)
    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsconcat.max_mem}g -jar {hipsconcat.alladin_cmd}"
    )

    concat_jobs = hipsconcat.make_concat_jobs()
    print("\n\nSubmitting concat jobs...")

    for job in concat_jobs:
        print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
