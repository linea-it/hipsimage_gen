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
    create_config_file,
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

        self.__job = None

    @property
    def job(self) -> Dict[str, str]:
        """Return the submitted job"""
        return self.__job

    def submit(self) -> Dict:
        """Submit a SLURM job to create an index

        Returns:
            Job info dict for the index creation job

        """

        config = self.config.copy()
        config["out"] = str(self.output_dir)

        config_output_path = str(self.output_dir / "config")

        config_file = create_config_file(config, config_output_path)
        cmd = prepare_sbatch_cmd(
            "index.sbatch",
            config_file=str(config_file),
            aladin_jar=self.alladin_cmd,
            max_mem=self.max_mem,
        )

        print(f"Submitting index job with command: {' '.join(cmd)}")

        if self.dryrun:
            job_id = "index.01"
            print("DRY RUN: would submit index job")
        else:
            job_id = submit_slurm_job(
                cmd,
                work_dir=str(self.output_dir.absolute()),
            )
            print(f"Submitted index job {job_id}")

        self.__job = {"id": job_id, "output_dir": str(self.output_dir.absolute())}
        return self.job


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

    print("/n/nSubmitting job...")
    job = hipsimage.submit()
    print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
