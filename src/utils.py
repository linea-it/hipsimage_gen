"""Utility functions for HiPS image generation."""

from pathlib import Path
import subprocess
from typing import Dict, List


def extract_unique_id_from_filename(file_path: Path, number: int = None) -> str:
    """
    Extract a unique ID from the filename

    Args:
        file_path: Path object of the file
        number: Optional number to append for uniqueness
    Returns:
        Unique ID string
    """
    if number:
        return f"{number:05d}"

    return f'{file_path.stem.replace(".", "_").replace("-", "_").replace(",", "_")}'


def create_config_by_band(config: Dict) -> Dict:
    """Create config dict organized by band (g, r, i)"""
    hips_config = config["hipsgen"]
    hips_runs = hips_config["runs"]

    band_to_color = {"g": "blue", "r": "green", "i": "red"}
    color_configs = {}

    for band, color in band_to_color.items():
        if color in hips_runs:
            color_config = hips_runs[color].copy()
            color_config.update(hips_config)
            color_config.pop("runs", None)  # Remove 'runs' key
            color_configs[band] = color_config

    return color_configs


def create_rgb_config(config: Dict) -> Dict:
    """Create config dict for RGB consolidation"""
    hips_config = config["hipsgen"]
    hips_runs = hips_config["runs"]

    rgb_config = hips_runs["rgb"].copy()
    rgb_config.update(hips_config)
    rgb_config.pop("runs", None)  # Remove 'runs' key

    return rgb_config


def create_config_file(
    base_config: Dict,
    output_dir: Path,
    add_output_path: bool = True,
) -> Path:
    """
    Create a config file for a specific image and band

    Args:
        base_config: Base configuration dictionary
        output_dir: Directory to save the config file
        add_output_path: Whether to add output path to config
    Returns:
        Path to the created config file
    """

    config_path = output_dir / "config"

    with open(config_path, "w", encoding="utf-8") as f:
        for key, value in base_config.items():
            if key == "runs":
                continue

            f.write(f'{key}="{value}"\n')

        # Add output directory
        if add_output_path:
            f.write(f'output="{(output_dir).absolute()}"\n')

    return config_path


def group_into_pairs(items: List) -> List[List]:
    """
    Groups list of items into pairs, leaving item alone if odd numbered

    Args:
        items: List of items to group

    Returns:
        List of pairs (sublists)
    """
    pairs = []
    for i in range(0, len(items), 2):
        if i + 1 < len(items):
            pairs.append([items[i], items[i + 1]])
        else:
            pairs.append([items[i]])  # Item sozinho
    return pairs


def submit_slurm_job(
    cmd: List[str],
    work_dir: Path,
) -> int:
    """Submit a SLURM job using sbatch and return the job ID.
    Args:
        cmd: List of command line arguments for sbatch
        work_dir: Working directory to submit the job from
    Returns:
        Job ID as an integer
    """

    try:
        result = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True, check=True
        )
        output = result.stdout.strip()

        if not "Submitted batch job" in output:
            raise RuntimeError(f"Response from sbatch unexpected: {output}")

        job_id = int(output.split()[-1])
        return job_id

    except subprocess.CalledProcessError as e:
        print(f"Erro no sbatch: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        raise
