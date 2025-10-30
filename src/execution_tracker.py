#!/usr/bin/env python3
"""Module to track execution time between HiPS creation phases."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


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
            phase_name: Name of the phase (index, regions, concat, concat_serial)
            job_id: Optional Slurm job ID associated with the phase
        """
        if phase_name not in self.tracking_data["phases"]:
            self.tracking_data["phases"][phase_name] = {
                "started_at": datetime.now().isoformat(),
                "job_ids": [],
                "status": "running",
            }

        if job_id:
            self.tracking_data["phases"][phase_name]["job_ids"].append(job_id)

        self._save_tracking_data()

    def add_phase_job(
        self, phase_name: str, job_id: int, metadata: Optional[Dict] = None
    ):
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
            "metadata": metadata or {},
        }

        self._save_tracking_data()

    def end_phase(self, phase_name: str):
        """Mark the end of a phase

        Args:
            phase_name: Name of the phase
        """
        if phase_name in self.tracking_data["phases"]:
            self.tracking_data["phases"][phase_name][
                "ended_at"
            ] = datetime.now().isoformat()
            self.tracking_data["phases"][phase_name]["status"] = "completed"
            self._save_tracking_data()

    def submitted_phase(self, phase_name: str):
        """Mark the submission of a phase

        Args:
            phase_name: Name of the phase
        """
        if phase_name in self.tracking_data["phases"]:
            self.tracking_data["phases"][phase_name][
                "submitted_at"
            ] = datetime.now().isoformat()
            self.tracking_data["phases"][phase_name]["status"] = "submitted"
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
                "-j",
                str(job_id),
                "--format=JobID,JobName,State,Start,End,Elapsed,CPUTime,MaxRSS,ExitCode",
                "--parsable2",
                "--noheader",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

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
                "exit_code": fields[8],
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
        self.calculate_times()

        report_lines = [
            "=" * 80,
            "HiPS Generation Execution Report",
            "=" * 80,
            "\n" + "-" * 80,
        ]

        for phase_name in ["index", "regions", "concat", "concat_serial"]:
            if phase_name not in self.tracking_data["phases"]:
                continue

            phase = self.tracking_data["phases"][phase_name]
            report_lines.append(f"Phase: {phase_name.upper()}")
            report_lines.append(f"  Status: {phase.get('status', 'unknown')}")
            report_lines.append(f"  Started: {phase.get('started_at', 'N/A')}")
            report_lines.append(f"  Ended: {phase.get('ended_at', 'N/A')}")
            report_lines.append(f"  Exec Time: {phase.get('exec_time', 'N/A')}")

            job_ids = phase.get("job_ids", [])
            report_lines.append(f"  Total Jobs: {len(job_ids)}")

            if job_ids:
                report_lines.append(f"  Job IDs: {', '.join(map(str, job_ids))}")

                # Aggregate statistics
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

                report_lines.append(f"  Completed: {completed}")
                report_lines.append(f"  Failed: {failed}")

            report_lines.append("-" * 80)

        # Overall summary
        if "ended_at" in self.tracking_data:
            report_lines.append(
                f"\nExecution Time: {self.tracking_data['total_execution_time']}\n"
            )

        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    # Função para analisar strings de data/hora.
    # Os tempos do SLURM estão sem microssegundos.
    def _parse_time(self, time_str: str) -> datetime:
        """Analyze datetime strings"""

        if time_str == "Unknown":
            return None

        try:
            # Tenta analisar com microssegundos
            # (de 'started_at' no JSON principal e blocos de fase)
            return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            return datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")

    def calculate_times(self) -> Dict[str, str]:
        """Times calculates"""
        results = {}
        job_details = self.tracking_data["jobs"]
        all_job_starts = []
        all_job_ends = []

        # 1. Calcular o tempo de execução para cada fase (Wall-Clock)
        phase_times = {}
        for phase_name, phase_info in self.tracking_data["phases"].items():
            phase_job_ids = [str(job_id) for job_id in phase_info["job_ids"]]
            job_starts = []
            job_ends = []

            # Encontrar os tempos de início e fim para todos os jobs na fase
            for job_id in phase_job_ids:
                if job_id in job_details:
                    slurm_info = job_details[job_id].get("slurm_info")
                    if slurm_info and slurm_info.get("start", None):
                        start_time = self._parse_time(slurm_info["start"])
                        if start_time:
                            job_starts.append(start_time)
                        all_job_starts.append(start_time)
                    if slurm_info and slurm_info.get("state") == "COMPLETED":
                        # Usar o tempo do SLURM (sem microssegundos)
                        end_time = self._parse_time(slurm_info["end"])
                        if end_time:
                            job_ends.append(end_time)
                            all_job_ends.append(end_time)

            if len(phase_job_ids) == len(job_ends):
                phase_info["status"] = "completed"
                phase_info["ended_at"] = str(max(job_ends))


            print(job_starts)
            print(job_ends)
            if job_starts and job_ends:
                # Tempo Wall-clock para a fase é do start mais cedo ao end mais tarde
                phase_start = min(job_starts)
                phase_end = max(job_ends)
                phase_duration = phase_end - phase_start
                phase_times[phase_name] = str(phase_duration)
                phase_info["exec_time"] = str(phase_duration)
            elif (
                (
                    phase_info["status"] == "completed"
                    or phase_info["status"] == "submitted"
                )
                and "started_at" in phase_info
                and "ended_at" in phase_info
            ):
                # Para fases concluídas que não têm jobs SLURM
                # (o que não parece o caso aqui, mas é uma reserva)
                start = self._parse_time(phase_info["started_at"])
                end = self._parse_time(phase_info["ended_at"])
                phase_times[phase_name] = str(end - start)
                phase_info["exec_time"] = str(end - start)
                phase_info["status"] = "completed"


        # 2. Calcular o tempo de execução total (Wall-Clock)
        if all_job_starts and all_job_ends:
            # O início geral é fornecido na estrutura JSON principal
            # (com microssegundos)
            overall_start = self._parse_time(self.tracking_data["started_at"])
            # O fim geral é o horário de término mais recente de
            # qualquer job concluído (tempo SLURM)
            overall_end = max(all_job_ends)
            total_wall_clock_duration = overall_end - overall_start
            results["total_execution_time"] = str(total_wall_clock_duration)
            self.tracking_data["ended_at"] = datetime.now().isoformat()
        else:
            results["total_execution_time"] = (
                "N/A (No completed jobs found with SLURM times)"
            )
        self.tracking_data["total_execution_time"] = results["total_execution_time"]

        results["phase_execution_times"] = phase_times
        self._save_tracking_data()

        # Retorna o dicionário de resultados
        return results

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
