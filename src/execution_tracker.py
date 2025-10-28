#!/usr/bin/env python3
"""Module to track execution time between HiPS creation phases."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ExecutionTracker:
    """Track execution time of HiPS creation phases using Slurm job info"""

    def __init__(self, output_dir: str):
        """Initialize the execution tracker
        
        Args:
            output_dir: Base output directory for tracking files
        """
        self.output_dir = Path(output_dir)
        self.tracking_file = self.output_dir / "execution_tracking.json"
        self.tracking_data = self._load_tracking_data()

    def _load_tracking_data(self) -> Dict:
        """Load existing tracking data or create new structure"""
        if self.tracking_file.exists():
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "phases": {},
            "jobs": {},
            "started_at": datetime.now().isoformat(),
        }

    def _save_tracking_data(self):
        """Save tracking data to file"""
        self.output_dir.mkdir(exist_ok=True)
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            json.dump(self.tracking_data, f, indent=2)

    def start_phase(self, phase_name: str, job_id: Optional[int] = None):
        """Mark the start of a phase
        
        Args:
            phase_name: Name of the phase (index, regions, concat)
            job_id: Optional Slurm job ID associated with the phase
        """
        if phase_name not in self.tracking_data["phases"]:
            self.tracking_data["phases"][phase_name] = {
                "started_at": datetime.now().isoformat(),
                "job_ids": [],
                "status": "running"
            }
        
        if job_id:
            self.tracking_data["phases"][phase_name]["job_ids"].append(job_id)
        
        self._save_tracking_data()

    def add_phase_job(self, phase_name: str, job_id: int, metadata: Optional[Dict] = None):
        """Add a job to a phase
        
        Args:
            phase_name: Name of the phase
            job_id: Slurm job ID
            metadata: Optional metadata about the job
        """
        if phase_name not in self.tracking_data["phases"]:
            self.start_phase(phase_name)
        
        if job_id not in self.tracking_data["phases"][phase_name]["job_ids"]:
            self.tracking_data["phases"][phase_name]["job_ids"].append(job_id)
        
        # Store job metadata
        self.tracking_data["jobs"][str(job_id)] = {
            "phase": phase_name,
            "submitted_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self._save_tracking_data()

    def end_phase(self, phase_name: str):
        """Mark the end of a phase
        
        Args:
            phase_name: Name of the phase
        """
        if phase_name in self.tracking_data["phases"]:
            self.tracking_data["phases"][phase_name]["ended_at"] = datetime.now().isoformat()
            self.tracking_data["phases"][phase_name]["status"] = "completed"
            self._save_tracking_data()

    def get_slurm_job_info(self, job_id: int) -> Optional[Dict]:
        """Get detailed information about a Slurm job using sacct
        
        Args:
            job_id: Slurm job ID
            
        Returns:
            Dictionary with job information or None if job not found
        """
        try:
            cmd = [
                "sacct",
                "-j", str(job_id),
                "--format=JobID,JobName,State,Start,End,Elapsed,CPUTime,MaxRSS,ExitCode",
                "--parsable2",
                "--noheader"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            lines = result.stdout.strip().split("\n")
            if not lines or not lines[0]:
                return None
            
            # Parse first line (main job info)
            fields = lines[0].split("|")
            if len(fields) < 9:
                return None
            
            return {
                "job_id": fields[0],
                "job_name": fields[1],
                "state": fields[2],
                "start": fields[3],
                "end": fields[4],
                "elapsed": fields[5],
                "cpu_time": fields[6],
                "max_rss": fields[7],
                "exit_code": fields[8]
            }
        except (subprocess.CalledProcessError, Exception) as e:
            print(f"Warning: Could not get info for job {job_id}: {e}")
            return None

    def update_jobs_info(self):
        """Update all tracked jobs with current Slurm information"""
        for job_id in self.tracking_data["jobs"].keys():
            job_info = self.get_slurm_job_info(int(job_id))
            if job_info:
                self.tracking_data["jobs"][job_id]["slurm_info"] = job_info
        
        self._save_tracking_data()

    def generate_report(self) -> str:
        """Generate a human-readable execution report
        
        Returns:
            Formatted string with execution statistics
        """
        self.update_jobs_info()
        
        report_lines = [
            "=" * 80,
            "HiPS Generation Execution Report",
            "=" * 80,
            f"\nStarted at: {self.tracking_data.get('started_at', 'N/A')}",
            "\n" + "-" * 80,
        ]
        
        for phase_name in ["index", "regions", "concat"]:
            if phase_name not in self.tracking_data["phases"]:
                continue
            
            phase = self.tracking_data["phases"][phase_name]
            report_lines.append(f"\nPhase: {phase_name.upper()}")
            report_lines.append(f"  Status: {phase.get('status', 'unknown')}")
            report_lines.append(f"  Started: {phase.get('started_at', 'N/A')}")
            report_lines.append(f"  Ended: {phase.get('ended_at', 'N/A')}")
            
            job_ids = phase.get("job_ids", [])
            report_lines.append(f"  Total Jobs: {len(job_ids)}")
            
            if job_ids:
                report_lines.append(f"  Job IDs: {', '.join(map(str, job_ids))}")
                
                # Aggregate statistics
                total_elapsed = 0
                completed = 0
                failed = 0
                
                for job_id in job_ids:
                    job_data = self.tracking_data["jobs"].get(str(job_id), {})
                    slurm_info = job_data.get("slurm_info", {})
                    
                    if slurm_info:
                        state = slurm_info.get("state", "")
                        if "COMPLETED" in state:
                            completed += 1
                        elif "FAILED" in state or "CANCELLED" in state:
                            failed += 1
                        
                        elapsed = slurm_info.get("elapsed", "")
                        if elapsed:
                            total_elapsed += self._parse_elapsed_time(elapsed)
                
                report_lines.append(f"  Completed: {completed}")
                report_lines.append(f"  Failed: {failed}")
                
                if total_elapsed > 0:
                    report_lines.append(f"  Total Elapsed Time: {self._format_seconds(total_elapsed)}")
                    if completed > 0:
                        avg_time = total_elapsed / completed
                        report_lines.append(f"  Average Job Time: {self._format_seconds(avg_time)}")
            
            report_lines.append("-" * 80)
        
        # Overall summary
        if "ended_at" in self.tracking_data:
            report_lines.append(f"\nCompleted at: {self.tracking_data['ended_at']}")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)

    def _parse_elapsed_time(self, elapsed_str: str) -> float:
        """Parse Slurm elapsed time string to seconds
        
        Args:
            elapsed_str: Time string in format DD-HH:MM:SS or HH:MM:SS
            
        Returns:
            Total seconds
        """
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

    def _format_seconds(self, seconds: float) -> str:
        """Format seconds to human-readable string
        
        Args:
            seconds: Number of seconds
            
        Returns:
            Formatted string (e.g., "2h 30m 15s")
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        
        return " ".join(parts)

    def save_report(self, output_path: Optional[str] = None):
        """Save execution report to file
        
        Args:
            output_path: Optional path for the report file
        """
        if output_path is None:
            output_path = self.output_dir / "execution_report.txt"
        
        report = self.generate_report()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"Execution report saved to: {output_path}")
