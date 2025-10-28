#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from yaml import safe_load


def main():
    """Main function to parse arguments and run HipsGen processing"""

    from hips_create_index import HipsCreateIndex
    from hips_parallel_by_regions import HipsParallelByRegions
    from hips_hierarchical_concat import HipsHierarchicalConcat
    from execution_tracker import ExecutionTracker

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

    # Load config to get output_dir for tracker
    with open(args.config, "r", encoding="utf-8") as f:
        config = safe_load(f)
    output_dir = config.get("output_dir", ".")
    
    # Initialize execution tracker
    tracker = ExecutionTracker(output_dir)

    phases = ["index", "regions", "concat"]

    index_path = jobs = None

    if args.phases:
        phases = args.phases
        phases = phases.split(",")

    if "index" in phases:
        tracker.start_phase("index")
        hipsindex = HipsCreateIndex(args.config)
        job = hipsindex.submit()
        index_path = job["output_dir"]
        tracker.add_phase_job("index", job["id"], {"output_dir": index_path})
        tracker.end_phase("index")

    if "regions" in phases:
        tracker.start_phase("regions")
        hipsimage = HipsParallelByRegions(args.config, index_path=index_path)
        jobs = hipsimage.submit_jobs()
        # Track all region jobs
        for job in jobs:
            tracker.add_phase_job("regions", job["id"], {
                "output_dir": job["output_dir"],
                "dependencies": job.get("slurm_job_dependencies", [])
            })
        tracker.end_phase("regions")

    if "concat" in phases:
        tracker.start_phase("concat")
        hipsconcat = HipsHierarchicalConcat(args.config, jobs=jobs)
        concat_jobs = hipsconcat.execute_hierarchical_concatenation()
        print("\n\nSubmitting concat job...")
        print(f"  Job: {concat_jobs}")
        # Track concat jobs (can be multiple)
        if isinstance(concat_jobs, list):
            for job in concat_jobs:
                tracker.add_phase_job("concat", job["id"], {
                    "output_dir": job.get("output_dir", ""),
                    "dependencies": job.get("slurm_job_dependencies", [])
                })
        else:
            tracker.add_phase_job("concat", concat_jobs["id"], {
                "output_dir": concat_jobs.get("output_dir", ""),
                "dependencies": concat_jobs.get("slurm_job_dependencies", [])
            })
        tracker.end_phase("concat")
    
    # Generate and save execution report
    print("\n" + "="*80)
    print(tracker.generate_report())
    tracker.save_report()


if __name__ == "__main__":
    sys.exit(main())
