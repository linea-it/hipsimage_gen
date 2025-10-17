#!/usr/bin/env python3
"""
Script para paralelização do HipsGen com concatenação hierárquica.

FLUXO DE PROCESSAMENTO:
1. Encontra arquivos particionados
2. Para cada cor (red, green, blue):
   - Executa HipsGen para cada partição em paralelo
   - Concatena hierarquicamente em pares até sobrar uma imagem
3. Consolida as 3 bandas finais em RGB

EXEMPLO COM 7 PARTIÇÕES:
  Nível 0: [P1] [P2] [P3] [P4] [P5] [P6] [P7]
  Nível 1: [P1+P2] [P3+P4] [P5+P6] [P7] ← P7 passa direto
  Nível 2: [P1234] [P567]
  Nível 3: [P1234567] ← Resultado final por banda
"""

import argparse
import re
import sys
from glob import glob
from pathlib import Path
from typing import Dict, List, Tuple

from yaml import safe_load

from utils import (
    create_config_file,
    group_into_pairs,
    submit_slurm_job,
    create_config_by_band,
)


class HipsHierarchicalConcatError(Exception):
    """Exceção personalizada para erros no HipsCreateByFile"""


class HipsHierarchicalConcat:
    """Class to handle HipsGen creation from config file"""

    def __init__(self, config: Dict, jobs: Dict) -> None:

        with open(config, "r", encoding="utf-8") as f:
            config = safe_load(f)

        self.config = create_config_by_band(config)
        self.dryrun = config.get("dryrun", False)
        config.pop("inputs", None)

        self.jobs_submited = jobs

        self.alladin_cmd = config.get("aladin_cmd", "Aladin.jar")
        self.max_mem = str(config.get("max_mem", "2"))
        self.output_dir = Path(config.get("output_dir", "."), "images")
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
                    print(f"Pair 1: {pair[0]}")
                    print(f"Pair 2: {pair[1]}")
                    # job_id = submit_slurm_job(
                    #     "concat.sbatch",

                    # )
                    output_job = pair[1]
                    output_job["id"] = f"concat_{level}.{idx}"
                    next_level_jobs.append(output_job)

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
    hipsconcat = HipsHierarchicalConcat(args.config, jobs)

    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsconcat.max_mem}g -jar {hipsconcat.alladin_cmd}"
    )
    print(f"Working directory: {hipsimage.output_dir}")

    print("jobs by imgs:")
    for band, value in hipsconcat.jobs_submited.items():
        print(f"--> Band: {band}")
        main_color_job = hipsconcat.recursive_hierarchical_concat(value)
        print(f"Final job for band {band}: {main_color_job}")
        print("-------\n")


if __name__ == "__main__":
    sys.exit(main())
