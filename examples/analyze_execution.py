#!/usr/bin/env python3
"""
Example script showing how to analyze execution tracking data programmatically.

This demonstrates how to:
- Load tracking data
- Calculate phase durations
- Identify slowest jobs
- Generate custom statistics
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def parse_iso_datetime(dt_str):
    """Parse ISO datetime string"""
    return datetime.fromisoformat(dt_str)


def parse_elapsed_time(elapsed_str):
    """Parse Slurm elapsed time to seconds"""
    try:
        parts = elapsed_str.split("-")
        if len(parts) == 2:
            days = int(parts[0])
            time_part = parts[1]
        else:
            days = 0
            time_part = parts[0]
        
        time_components = time_part.split(":")
        hours = int(time_components[0])
        minutes = int(time_components[1])
        seconds = int(time_components[2])
        
        return days * 86400 + hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return 0


def analyze_tracking_data(output_dir):
    """Analyze execution tracking data and generate custom statistics"""
    
    tracking_file = Path(output_dir) / "execution_tracking.json"
    if not tracking_file.exists():
        print(f"Error: Tracking file not found at {tracking_file}")
        return
    
    with open(tracking_file, "r") as f:
        data = json.load(f)
    
    print("="*80)
    print("Custom Execution Analysis")
    print("="*80)
    print()
    
    # Overall timing
    started = parse_iso_datetime(data.get("started_at", ""))
    print(f"Pipeline started: {started.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Phase analysis
    phases = data.get("phases", {})
    jobs_data = data.get("jobs", {})
    
    for phase_name in ["index", "regions", "concat"]:
        if phase_name not in phases:
            continue
        
        phase = phases[phase_name]
        print(f"\n{'='*80}")
        print(f"Phase: {phase_name.upper()}")
        print(f"{'='*80}")
        
        # Phase duration
        if "started_at" in phase and "ended_at" in phase:
            phase_start = parse_iso_datetime(phase["started_at"])
            phase_end = parse_iso_datetime(phase["ended_at"])
            phase_duration = (phase_end - phase_start).total_seconds()
            print(f"Phase duration: {phase_duration/3600:.2f} hours")
        
        # Jobs analysis
        job_ids = phase.get("job_ids", [])
        print(f"Total jobs: {len(job_ids)}")
        
        job_times = []
        completed_jobs = []
        failed_jobs = []
        
        for job_id in job_ids:
            job_data = jobs_data.get(str(job_id), {})
            slurm_info = job_data.get("slurm_info", {})
            
            if slurm_info:
                state = slurm_info.get("state", "")
                elapsed = slurm_info.get("elapsed", "")
                
                if elapsed:
                    elapsed_seconds = parse_elapsed_time(elapsed)
                    job_times.append({
                        "job_id": job_id,
                        "elapsed": elapsed_seconds,
                        "elapsed_str": elapsed
                    })
                
                if "COMPLETED" in state:
                    completed_jobs.append(job_id)
                elif "FAILED" in state or "CANCELLED" in state:
                    failed_jobs.append(job_id)
        
        print(f"Completed: {len(completed_jobs)}")
        print(f"Failed: {len(failed_jobs)}")
        
        if job_times:
            # Statistics
            times = [j["elapsed"] for j in job_times]
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"\nJob Duration Statistics:")
            print(f"  Average: {avg_time/60:.2f} minutes")
            print(f"  Minimum: {min_time/60:.2f} minutes")
            print(f"  Maximum: {max_time/60:.2f} minutes")
            
            # Find slowest jobs
            sorted_jobs = sorted(job_times, key=lambda x: x["elapsed"], reverse=True)
            print(f"\nTop 5 slowest jobs:")
            for i, job in enumerate(sorted_jobs[:5], 1):
                print(f"  {i}. Job {job['job_id']}: {job['elapsed_str']}")
            
            # Parallel efficiency (for regions phase)
            if phase_name == "regions" and len(times) > 1:
                total_time = sum(times)
                wall_time = phase_duration if 'phase_duration' in locals() else 0
                if wall_time > 0:
                    parallel_efficiency = (total_time / wall_time) / len(times) * 100
                    print(f"\nParallel Efficiency: {parallel_efficiency:.1f}%")
                    print(f"  Total CPU time: {total_time/3600:.2f} hours")
                    print(f"  Wall clock time: {wall_time/3600:.2f} hours")
                    print(f"  Speedup: {total_time/wall_time:.1f}x")
    
    print("\n" + "="*80)
    print("Analysis complete")
    print("="*80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_execution.py <output_dir>")
        print("Example: python analyze_execution.py /mnt/data/hips/output")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    analyze_tracking_data(output_dir)


if __name__ == "__main__":
    main()
