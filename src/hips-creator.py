#!/usr/bin/env python3

import argparse
import sys


def main():
    """Main function to parse arguments and run HipsGen processing"""

    from hips_create_index import HipsCreateIndex
    from hips_parallel_by_regions import HipsParallelByRegions
    from hips_hierarchical_concat import HipsHierarchicalConcat

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

    parser.add_argument(
        "-p",
        "--phases",
        type=str,
        help="Executes a specific phases: index, regions and concat",
    )

    args = parser.parse_args()

    phases = ["index", "regions", "concat"]

    index_path = jobs = None

    if args.phases:
        phases = args.phases
        phases = phases.split(",")

    if "index" in phases:
        hipsindex = HipsCreateIndex(args.config)
        job = hipsindex.submit()
        index_path = job["output_dir"]

    if "regions" in phases:
        hipsimage = HipsParallelByRegions(args.config, index_path=index_path)
        jobs = hipsimage.submit_jobs()

    if "concat" in phases:
        hipsconcat = HipsHierarchicalConcat(args.config, jobs=jobs)
        job = hipsconcat.execute_hierarchical_concatenation()
        print("\n\nSubmitting concat job...")
        print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
