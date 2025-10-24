#!/usr/bin/env python3

import argparse
import sys


def main():
    """Main function to parse arguments and run HipsGen processing"""

    from hips_create_index import HipsCreateIndex
    from hips_parallel_by_regions import HipsParallelByRegions
    from hips_concat import HipsConcat
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
        "-m",
        "--mode",
        type=str,
        default="single",
        help="Mode to run the script (single or hierarchical)",
    )

    args = parser.parse_args()

    hipsindex = HipsCreateIndex(args.config)
    job = hipsindex.submit()
    index_path = job["output_dir"]

    hipsimage = HipsParallelByRegions(args.config, index_path)
    jobs = hipsimage.submit_jobs()

    print("\nStarting HipsGen processing...")
    print(
        f"Using Aladin command: java -Xmx{hipsimage.max_mem}g -jar {hipsimage.alladin_cmd}"
    )

    if args.mode == "hierarchical":
        hipsconcat = HipsHierarchicalConcat(args.config, jobs)
        concat_jobs = hipsconcat.execute_hierarchical_concatenation()
    else:
        hipsconcat = HipsConcat(args.config, jobs)
        concat_jobs = hipsconcat.make_concat_jobs()

    print("\n\nSubmitting concat jobs...")
    for job in concat_jobs:
        print(f"  Job: {job}")


if __name__ == "__main__":
    sys.exit(main())
