#!/usr/bin/env python3

import argparse
import sys


def main():
    """Main function to parse arguments and run HipsGen processing"""

    from hips_create_index import HipsCreateIndex
    from hips_parallel_by_regions import HipsParallelByRegions
    from hips_concat import HipsConcat

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
