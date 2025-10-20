"""Module to create HipsGen indexes from a configuration file."""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

from yaml import safe_load

from utils import (
    prepare_sbatch_cmd,
    submit_slurm_job,
    create_index_config,
)


class HipsCreateIndexError(Exception):
    """Exceção personalizada para erros no HipsCreateIndex"""


class HipsCreateIndex:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.config = create_index_config(config)
        self.dryrun = config.get("dryrun", False)
        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "index")
        self.output_dir.mkdir(exist_ok=True)
        self.norders = range(13)

        self.__jobs_submitted = []

    @property
    def jobs_submitted(self) -> Dict[str, List[Dict]]:
        """Return the submitted jobs"""
        return self.__jobs_submitted

    def create_config_file(self, config, config_output_path: Path):
        """Create config"""

        with open(config_output_path, "w", encoding="utf-8") as f:
            for key, value in config.items():
                if key == "runs":
                    continue

                f.write(f'{key}="{value}"\n')

        return config_output_path

    def submit_jobs(self):
        """Submit jobs to SLURM for each norder"""

        for norder in self.norders:
            job_id = self.submit_by_norder(norder)
            self.__jobs_submitted.append(job_id)
        return self.jobs_submitted

    def submit_by_norder(self, norder: int) -> Dict:
        """Submit a SLURM job to create an index for a specific norder

        Args:
            norder: The norder level for which to create the index

        Returns:
            Job info dict for the index creation job

        """

        config = self.config.copy()
        config["order"] = str(norder)
        config["out"] = str(self.output_dir)

        config_output_path = str(self.output_dir / f"Norder{norder}")

        config_file = self.create_config_file(config, config_output_path)
        cmd = prepare_sbatch_cmd(
            "index.sbatch",
            config_file=str(config_file),
            aladin_jar=self.alladin_cmd,
            max_mem=self.max_mem,
        )

        print(f"Submitting index job for norder {norder} with command: {' '.join(cmd)}")

        if self.dryrun:
            job_id = f"index.Norder{norder}"
            print(f"DRY RUN: would submit index job for norder {norder}")
        else:
            job_id = submit_slurm_job(
                cmd,
                work_dir=str(self.output_dir.absolute()),
            )
            print(f"Submitted index job {job_id} for norder {norder}")

        return job_id


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
    hipsimage = HipsCreateIndex(args.config)

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
