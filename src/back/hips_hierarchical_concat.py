#!/usr/bin/env python3
""" """

import argparse
import re
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


class HipsHierarchicalConcatError(Exception):
    """Exceção personalizada para erros no HipsCreateByFile"""


class HipsHierarchicalConcat:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.config = create_concat_config(config)
        self.dryrun = config.get("dryrun", False)
        config.pop("inputs", None)

        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "main")
        self.output_dir.mkdir(exist_ok=True)

    def recursive_hierarchical_concat(
        self,
        current_level_outputs: List[Dict],
    ) -> Tuple[str, List[int]]:
        """Perform hierarchical concatenation of HipsGen outputs

        Args:
            current_level_outputs: List of current level output file paths
        Returns:
            Final output file path and list of all job IDs
        """

        level = 1

        while len(current_level_outputs) >= 1:
            print(f"--- Level {level} = total jobs: {len(current_level_outputs)} ---")
            pairs = group_into_pairs(current_level_outputs)
            next_level_jobs = []

            for idx, pair in enumerate(pairs, start=1):

                if len(current_level_outputs) == 1 and len(pair) == 1:
                    print("Only one file remaining, final output reached.")
                    return pair

                if len(pair) == 1:
                    print(f"Pass through to next level: {pair[0]}")
                    next_level_jobs.append(pair[0])
                else:
                    config_concat = self.config.copy()
                    config_concat["in"] = pair[0]["output_dir"]
                    config_concat["out"] = pair[1]["output_dir"]

                    config_file = create_config_file(
                        config_concat,
                        Path(pair[1]["output_dir"]),
                        add_output_path=False,
                    )

                    dependencies = [
                        pair[0]["id"],
                        pair[1]["id"],
                    ]
                    cmd = prepare_sbatch_cmd(
                        "concat.sbatch",
                        config_file=str(config_file),
                        aladin_jar=self.alladin_cmd,
                        max_mem=self.max_mem,
                        dependency=":".join(map(str, dependencies)),
                    )

                    print(f"Submitting concat job with command: {' '.join(cmd)}")

                    if self.dryrun:
                        job_id = f"concat_{level}.{idx}"
                        print(f"DRY RUN: would submit concat job {job_id}")
                    else:
                        job_id = submit_slurm_job(
                            cmd,
                            work_dir=str(self.output_dir.parent.absolute()),
                        )

                    job = {
                        "id": job_id,
                        "output_dir": pair[1]["output_dir"],
                        "slurm_job_dependencies": dependencies,
                    }

                    next_level_jobs.append(job)
            current_level_outputs = next_level_jobs
            level += 1

        return current_level_outputs


def main():
    """Main function to parse arguments and run HipsGen processing"""
    from hips_create_by_file import HipsCreateByFile

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
    jobs = hipsimage.submit_jobs()
    print(f"Total jobs submitted: {len(jobs)}")
    print(f"Jobs: {jobs}")

    hipsconcat = HipsHierarchicalConcat(args.config)
    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsconcat.max_mem}g -jar {hipsconcat.alladin_cmd}"
    )
    print(f"Working directory: {hipsimage.output_dir}")
    main_job = hipsconcat.recursive_hierarchical_concat(jobs)
    print(f"Final job: {main_job}")


if __name__ == "__main__":
    sys.exit(main())
