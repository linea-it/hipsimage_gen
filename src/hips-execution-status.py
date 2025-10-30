#!/usr/bin/env python3
"""Query and display HiPS execution tracking information."""

import json
import argparse
import sys
from pathlib import Path

from execution_tracker import ExecutionTracker


def main():
    """Main function to query execution status"""

    parser = argparse.ArgumentParser(
        description="Query HiPS execution tracking information"
    )
    parser.add_argument(
        "-d",
        "--output-dir",
        type=str,
        required=True,
        help="Output directory containing execution_tracking.json",
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Update job information from Slurm before displaying report",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Save report to specified file",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="Display raw JSON tracking data",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        print(f"Error: Output directory {output_dir} does not exist")
        return 1

    tracking_file = output_dir / "execution_tracking.json"
    if not tracking_file.exists():
        print(f"Error: No tracking file found at {tracking_file}")
        print("Run hips-creator with tracking enabled first.")
        return 1

    tracker = ExecutionTracker(args.output_dir)

    if args.update:
        print("Updating job information from Slurm...")
        tracker.update_jobs_info()
        print("Update complete.\n")

    if args.json:
        print(json.dumps(tracker.tracking_data, indent=2))
    else:
        report = tracker.generate_report()
        print(report)

        if args.output:
            tracker.save_report(args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
