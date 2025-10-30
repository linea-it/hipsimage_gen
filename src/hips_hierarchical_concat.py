#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from yaml import safe_load

from utils import (
    prepare_sbatch_cmd,
    create_concat_config,
    submit_slurm_job,
    create_config_file,
    group_into_pairs,
)


class HipsHierarchicalConcat:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict, jobs: List[Dict] = None) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.config = create_concat_config(config)
        self.dryrun = config.get("dryrun", False)
        self.creator_did = config.get("hipsgen", {}).pop("creator_did", "CDS/P/HIPS")
        config.get("hipsgen", {}).pop("hips_creator", None)
        config.get("hipsgen", {}).pop("obs_title", None)

        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "concat")
        self.output_dir.mkdir(exist_ok=True)

        if not jobs:
            jobs = self.__get_jobs_from_dir(Path(self.output_dir).parent)

        self.__jobs = self.__sorted_jobs(jobs)

    @property
    def jobs(self) -> List[Dict]:
        """Return the submitted jobs"""
        return self.__jobs

    def __get_jobs_from_dir(self, dir_path: Path) -> List[Dict]:
        """Get jobs from directory"""

        regions_path = dir_path / "regions"

        jobs = []
        for job_dir in regions_path.glob("*"):
            if job_dir.is_dir():
                job = {
                    "output_dir": f"{str(job_dir)}/rgb",
                }
                jobs.append(job)

        return jobs

    def __sorted_jobs(self, jobs: List[Dict]):
        """Sort jobs by npixs"""

        for job in jobs:
            npixs = int(Path(job.get("output_dir")).parent.name.split(".")[-1])
            job["npixs"] = npixs
            job.pop("slurm_job_dependencies", None)

        return sorted(jobs, key=lambda x: x["npixs"])

    def execute_hierarchical_concatenation(self) -> Tuple[str, List[int]]:
        """Execute hierarchical concatenation"""

        current_level_outputs = self.jobs.copy()
        level = 0
        jobs = []

        print(f"Beginning with {len(current_level_outputs)} partitions")

        while len(current_level_outputs) > 1:
            level += 1
            pairs = group_into_pairs(current_level_outputs)
            next_level_outputs = []

            print(f"  Level {level}: {len(pairs)} concat")

            for pair_idx, pair in enumerate(pairs):
                job_in = pair[0]
                if len(pair) == 1:
                    # Item alone, skips directly to the next level.
                    next_level_outputs.append(job_in)
                    continue

                job_out = pair[1]
                pair_id = f"{level}_{pair_idx}"

                config_concat = self.config.copy()
                config_concat["in"] = job_in.get("output_dir")
                config_concat["out"] = job_out.get("output_dir")
                concat_tmp_dir = Path(job_out.get("output_dir")) / "concat-tmp"
                concat_tmp_dir.mkdir(exist_ok=True)
                config_concat["cache"] = str(concat_tmp_dir)
                config_concat["creator_did"] = f"{self.creator_did}/{pair_id}"

                config_file = create_config_file(
                    config_concat,
                    str(self.output_dir / f"{pair_id}.config"),
                )

                dependencies = [
                    dep
                    for dep in set(
                        [
                            job_in.get("id", None),
                            job_out.get("id", None),
                        ]
                    )
                    if dep is not None
                ]

                if dependencies:
                    dep_str = ":".join(map(str, dependencies))
                else:
                    dep_str = None

                cmd = prepare_sbatch_cmd(
                    "concat.sbatch",
                    config_file=str(config_file),
                    aladin_jar=self.alladin_cmd,
                    max_mem=self.max_mem,
                    dependency=dep_str,
                )

                print(f"Submitting concat job with command: {' '.join(cmd)}")

                if self.dryrun:
                    job_id = pair_id
                    print(f"DRY RUN: would submit concat job {job_id}")
                else:
                    job_id = submit_slurm_job(
                        cmd,
                        work_dir=str(self.output_dir.absolute()),
                    )
                    print(f"Submitted concat job {job_id}")

                job = {
                    "id": job_id,
                    "output_dir": job_out.get("output_dir"),
                    "slurm_job_dependencies": dependencies,
                }

                jobs.append(job)
                next_level_outputs.append(job)

            current_level_outputs = next_level_outputs

        print(f"  Jobs: {jobs}")
        return jobs


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

    hipsindex = HipsCreateIndex(args.config)
    job = hipsindex.submit()
    index_path = job["output_dir"]

    hipsimage = HipsParallelByRegions(args.config, index_path)
    jobs = hipsimage.submit_jobs()

    hipsconcat = HipsHierarchicalConcat(args.config, jobs)
    jobs = hipsconcat.execute_hierarchical_concatenation()
    print(f"  Jobs: {jobs}")


if __name__ == "__main__":
    sys.exit(main())
