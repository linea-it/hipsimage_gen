#!/usr/bin/env python3
""" """

import argparse
import shutil
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


class HipsHierarchicalConcatError(Exception):
    """ """


class HipsHierarchicalConcat:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict, jobs: List[Dict]) -> None:

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
        self.__jobs = self.__sorted_jobs(jobs)

        for job in self.__jobs:
            job_output = Path(job["output_dir"])
            print(job_output)

    @property
    def jobs(self) -> List[Dict]:
        """Return the submitted jobs"""
        return self.__jobs

    def __sorted_jobs(self, jobs: List[Dict]):
        """Sort jobs by npixs"""

        for job in jobs:
            npixs = int(Path(job.get("output_dir")).parent.name.split(".")[-1])
            job["npixs"] = npixs
            job.pop("slurm_job_dependencies", None)

        return sorted(jobs, key=lambda x: x["npixs"])

    def execute_hierarchical_concatenation(self) -> Tuple[str, List[int]]:
        """NOne"""
        current_level_outputs = self.jobs.copy()
        level = 0

        print(f"Iniciando com {len(current_level_outputs)} partitions")

        while len(current_level_outputs) > 1:
            level += 1
            pairs = group_into_pairs(current_level_outputs)
            next_level_outputs = []

            print(f"  Level {level}: {len(pairs)} concat")

            for pair_idx, pair in enumerate(pairs):
                job_in = pair[0]
                if len(pair) == 1:
                    # Item sozinho, passa direto para próximo nível
                    next_level_outputs.append(job_in)
                    continue

                job_out = pair[1]
                pair_id = f"{level}_{pair_idx}"

                config_concat = self.config.copy()
                config_concat["in"] = job_in.get("output_dir")
                config_concat["out"] = job_out.get("output_dir")
                config_concat["creator_did"] = f"{self.creator_did}/{pair_id}"

                config_file = create_config_file(
                    config_concat,
                    str(self.output_dir / f"{pair_id}.config"),
                )

                dependencies = [
                    job_in.get("id"),
                    job_out.get("id"),
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
                    job_id = pair_id
                    print(f"DRY RUN: would submit concat job {job_id}")
                else:
                    job_id = submit_slurm_job(
                        cmd,
                        work_dir=str(self.output_dir.parent.absolute()),
                    )
                    print(f"Submitted concat job {job_id}")

                job = {
                    "id": job_id,
                    "output_dir": job_out.get("output_dir"),
                    "slurm_job_dependencies": dependencies,
                }

                next_level_outputs.append(job)

            current_level_outputs = next_level_outputs

        main_job = current_level_outputs[0]
        print(f"  Resultado final: {main_job}")

        return main_job


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
    # index_path = job["output_dir"]

    # hipsimage = HipsParallelByRegions(args.config, index_path)
    # jobs = hipsimage.submit_jobs()

    jobs = [
        {
            "id": "rgb.11.47520001-47521151",
            "output_dir": "/mnt/EXT4/hips/dc2/test02/bands/11.47520001-47521151.337/rgb",
            "slurm_job_dependencies": [
                "g.11.47520001-47521151",
                "r.11.47520001-47521151",
                "i.11.47520001-47521151",
            ],
        },
        {
            "id": "rgb.11.47530496-47537770",
            "output_dir": "/mnt/EXT4/hips/dc2/test02/bands/11.47530496-47537770.1790/rgb",
            "slurm_job_dependencies": [
                "g.11.47530496-47537770",
                "r.11.47530496-47537770",
                "i.11.47530496-47537770",
            ],
        },
        {
            "id": "rgb.11.47518557-47519863",
            "output_dir": "/mnt/EXT4/hips/dc2/test02/bands/11.47518557-47519863.643/rgb",
            "slurm_job_dependencies": [
                "g.11.47518557-47519863",
                "r.11.47518557-47519863",
                "i.11.47518557-47519863",
            ],
        },
    ]

    hipsconcat = HipsHierarchicalConcat(args.config, jobs)
    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsconcat.max_mem}g -jar {hipsconcat.alladin_cmd}"
    )

    job = hipsconcat.execute_hierarchical_concatenation()
    print("\n\nSubmitting concat jobs...")

    print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
