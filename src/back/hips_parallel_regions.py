#!/usr/bin/env python3
"""
Script para paralelização do HipsGen usando regiões baseadas em coordenadas
dos dados fotométricos, sem necessidade de criar MOCs.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from astropy.io import fits
import h5py
import argparse
import subprocess
from dataclasses import replace
from yaml import safe_load

# Importa as classes do seu código original
from schemas import ColorConfig


def detect_file_format(file_path: str) -> str:
    """Detecta o formato do arquivo baseado na extensão"""
    suffix = Path(file_path).suffix.lower()
    format_map = {
        '.fits': 'fits', '.fit': 'fits',
        '.parquet': 'parquet', '.pq': 'parquet', 
        '.h5': 'hdf5', '.hdf5': 'hdf5', '.hdf': 'hdf5',
        '.csv': 'csv', '.txt': 'txt', '.dat': 'txt'
    }
    return format_map.get(suffix, 'unknown')


def get_coordinates_bounds(file_path: str, ra_col: str = 'ra', dec_col: str = 'dec', 
                          hdf5_table: Optional[str] = None) -> Tuple[float, float, float, float]:
    """
    Extrai os limites das coordenadas (ra_min, ra_max, dec_min, dec_max) dos dados fotométricos
    
    Args:
        file_path: Caminho para o arquivo de dados
        ra_col: Nome da coluna RA
        dec_col: Nome da coluna DEC  
        hdf5_table: Nome da tabela no HDF5 (opcional)
        
    Returns:
        Tupla (ra_min, ra_max, dec_min, dec_max) em graus
    """
    format_type = detect_file_format(file_path)
    print(f"Analisando arquivo {format_type}: {file_path}")
    
    if format_type == 'fits':
        with fits.open(file_path) as hdul:
            for i, hdu in enumerate(hdul):
                if hasattr(hdu, 'data') and hdu.data is not None:
                    try:
                        if hasattr(hdu.data, 'dtype') and len(hdu.data.dtype) > 0:
                            # Verifica se as colunas existem
                            colnames = hdu.data.dtype.names
                            if ra_col in colnames and dec_col in colnames:
                                ra = hdu.data[ra_col]
                                dec = hdu.data[dec_col]
                                break
                    except:
                        continue
        
    elif format_type == 'parquet':
        # Lê apenas as colunas necessárias para otimizar memória
        df = pd.read_parquet(file_path, columns=[ra_col, dec_col])
        ra = df[ra_col].values
        dec = df[dec_col].values
        
    elif format_type == 'hdf5':
        if hdf5_table:
            df = pd.read_hdf(file_path, key=hdf5_table, columns=[ra_col, dec_col])
        else:
            df = pd.read_hdf(file_path, columns=[ra_col, dec_col])
        ra = df[ra_col].values
        dec = df[dec_col].values
        
    elif format_type == 'csv':
        df = pd.read_csv(file_path, usecols=[ra_col, dec_col])
        ra = df[ra_col].values
        dec = df[dec_col].values
        
    elif format_type == 'txt':
        # Assume primeira coluna = RA, segunda = DEC
        data = np.loadtxt(file_path)
        ra = data[:, 0] if ra_col == '0' or ra_col == 'ra' else data[:, int(ra_col)]
        dec = data[:, 1] if dec_col == '1' or dec_col == 'dec' else data[:, int(dec_col)]
        
    else:
        raise ValueError(f"Formato não suportado: {format_type}")
    
    # Remove valores inválidos
    valid_mask = np.isfinite(ra) & np.isfinite(dec)
    ra_clean = ra[valid_mask]
    dec_clean = dec[valid_mask]
    
    if len(ra_clean) == 0:
        raise ValueError("Nenhuma coordenada válida encontrada")
    
    ra_min, ra_max = float(np.min(ra_clean)), float(np.max(ra_clean))
    dec_min, dec_max = float(np.min(dec_clean)), float(np.max(dec_clean))
    
    print(f"  {len(ra_clean)} objetos válidos de {len(ra)} total")
    print(f"  Limites: RA [{ra_min:.4f}, {ra_max:.4f}], DEC [{dec_min:.4f}, {dec_max:.4f}]")
    print(f"  Área coberta: {ra_max - ra_min:.4f}° × {dec_max - dec_min:.4f}°")
    
    return ra_min, ra_max, dec_min, dec_max


def calculate_regions(ra_min: float, ra_max: float, dec_min: float, dec_max: float,
                     num_regions_x: int, num_regions_y: int) -> List[Dict]:
    """
    Calcula as regiões retangulares para paralelização
    
    Args:
        ra_min, ra_max, dec_min, dec_max: Limites das coordenadas
        num_regions_x: Número de divisões em RA
        num_regions_y: Número de divisões em DEC
        
    Returns:
        Lista de dicionários com informações das regiões
    """
    ra_step = (ra_max - ra_min) / num_regions_x
    dec_step = (dec_max - dec_min) / num_regions_y
    
    regions = []
    
    print(f"Dividindo em {num_regions_x}×{num_regions_y} = {num_regions_x * num_regions_y} regiões:")
    
    for i in range(num_regions_x):
        for j in range(num_regions_y):
            ra1 = ra_min + i * ra_step
            ra2 = ra_min + (i + 1) * ra_step if i < num_regions_x - 1 else ra_max
            dec1 = dec_min + j * dec_step
            dec2 = dec_min + (j + 1) * dec_step if j < num_regions_y - 1 else dec_max
            
            region = {
                'id': f'region_{i}_{j}',
                'coords': f'{ra1},{dec1},{ra2},{dec2}',
                'ra_range': (ra1, ra2),
                'dec_range': (dec1, dec2),
                'output_suffix': f'_r{i}c{j}'
            }
            
            regions.append(region)
            
            print(f"  {region['id']}: RA[{ra1:.4f},{ra2:.4f}] DEC[{dec1:.4f},{dec2:.4f}]")
    
    return regions


def create_config_with_region(base_config: Dict, region: Dict, output_dir: Path) -> Path:
    """
    Cria arquivo de configuração para uma região específica
    
    Args:
        base_config: Configuração base do HipsGen
        region: Informações da região
        output_dir: Diretório de trabalho
        
    Returns:
        Caminho do arquivo de configuração criado
    """
    config_name = f"{region['id']}.config"
    config_path = output_dir / config_name
    
    with open(config_path, 'w') as f:
        # Copia parâmetros base
        for key, value in base_config.items():
            if key == 'input_dir':
                f.write(f'in="{Path(value).absolute()}"\n')
            elif key == 'output_dir':
                # Adiciona sufixo da região
                output_path = Path(output_dir, f"{value}{region['output_suffix']}")
                output_path.mkdir(exist_ok=True)
                f.write(f'out="{output_path.absolute()}"\n')
            elif key == 'cache':
                # Cache específico por região
                cache_path = Path(output_dir, f"{value}{region['output_suffix']}")
                cache_path.mkdir(exist_ok=True)
                f.write(f'cache="{cache_path.absolute()}"\n')
            else:
                f.write(f'{key}="{value}"\n')
        
        # Adiciona parâmetro de região
        f.write(f'region="{region["coords"]}"\n')
    
    return config_path


def create_consolidation_config(base_config: Dict, regions: List[Dict], 
                              output_dir: Path, final_output: str) -> Path:
    """
    Cria configuração para consolidação das regiões
    """
    config_path = output_dir / "consolidate.config"
    
    # Diretórios de entrada são os outputs das regiões
    input_dirs = []
    for region in regions:
        region_output = f"{base_config['output_dir']}{region['output_suffix']}"
        input_dirs.append(str(Path(output_dir, region_output).absolute()))
    
    with open(config_path, 'w') as f:
        # Múltiplos inputs separados por vírgula
        f.write(f'in="{",".join(input_dirs)}"\n')
        
        # Output final
        final_output_path = Path(output_dir, final_output)
        final_output_path.mkdir(exist_ok=True)
        f.write(f'out="{final_output_path.absolute()}"\n')
        
        # Outros parâmetros (sem região - vai consolidar tudo)
        for key, value in base_config.items():
            if key not in ['input_dir', 'output_dir', 'cache']:
                f.write(f'{key}="{value}"\n')
    
    return config_path


def submit_slurm_job(sbatch_script: str, config_file: Path, work_dir: Path, 
                    aladin_jar: str, max_mem: str, dependency: Optional[str] = None) -> int:
    """
    Submete job no Slurm e retorna o job ID
    """
    cmd = ["sbatch"]
    
    if dependency:
        cmd.extend(["--dependency", f"afterok:{dependency}"])
    
    cmd.extend([sbatch_script, max_mem, aladin_jar, str(config_file)])
    
    try:
        print(f"cmd: {cmd}")
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, check=True)
        
        # Extrai job ID da saída
        output = result.stdout.strip()
        if "Submitted batch job" in output:
            job_id = int(output.split()[-1])
            return job_id
        else:
            raise RuntimeError(f"Resposta inesperada do sbatch: {output}")
            
    except subprocess.CalledProcessError as e:
        print(f"Erro no sbatch: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        raise


def main():
    parser = argparse.ArgumentParser(description='HipsGen com paralelização por regiões')
    parser.add_argument('config_file', help='Arquivo de configuração YAML')
    parser.add_argument('photometry_file', help='Arquivo com dados fotométricos')
    parser.add_argument('--ra-col', default='ra', help='Nome da coluna RA')
    parser.add_argument('--dec-col', default='dec', help='Nome da coluna DEC')
    parser.add_argument('--nx', type=int, default=2, help='Divisões em RA')
    parser.add_argument('--ny', type=int, default=2, help='Divisões em DEC')
    parser.add_argument('--hdf5-table', help='Tabela HDF5')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simula, não submete jobs')
    
    args = parser.parse_args()
    
    # Lê configuração
    with open(args.config_file, 'r') as f:
        config = safe_load(f)
    
    # Extrai coordenadas dos dados
    try:
        ra_min, ra_max, dec_min, dec_max = get_coordinates_bounds(
            args.photometry_file, args.ra_col, args.dec_col, args.hdf5_table
        )
    except Exception as e:
        print(f"Erro ao ler coordenadas: {e}")
        return 1
    
    # Calcula regiões
    regions = calculate_regions(ra_min, ra_max, dec_min, dec_max, args.nx, args.ny)
    
    # Configurações
    cwd = Path(config.get("cwd", "."))
    cwd.mkdir(exist_ok=True)
    aladin_cmd = config.get("aladin_cmd", "Aladin.jar")
    max_mem = str(config.get("max_mem", "2"))
    
    hips_config = config['hipsgen']
    hips_runs = hips_config['runs']
    
    # Scripts Slurm
    sbatch_color = "color.sbatch"  # Assume que existe no PATH
    sbatch_consolidate = "consolidate.sbatch"  # Novo script para consolidação
    
    print(f"\n=== Processando {len(regions)} regiões ===")
    
    # Para cada cor
    colors = ["red", "green", "blue"]
    all_jobs = {}  # {color: [job_ids]}
    
    for color in colors:
        print(f"\n--- Processando cor: {color} ---")
        
        color_config = hips_runs[color].copy()
        color_config.update(hips_config)
        
        region_jobs = []
        
        # Job por região
        for region in regions:
            config_file = create_config_with_region(color_config, region, cwd)
            print(f"  Configuração criada: {config_file}")
            
            if not args.dry_run:
                job_id = submit_slurm_job(sbatch_color, config_file, cwd, aladin_cmd, max_mem)
                region_jobs.append(job_id)
                print(f"  Job submetido: {job_id} ({region['id']})")
            else:
                print(f"  [DRY RUN] Submeteria job para {region['id']}")
        
        all_jobs[color] = region_jobs
    
    # Jobs de consolidação por cor
    consolidate_jobs = []
    final_outputs = {}
    
    for color in colors:
        if not all_jobs[color]:
            continue
            
        print(f"\n--- Consolidação da cor: {color} ---")
        
        color_config = hips_runs[color].copy()
        color_config.update(hips_config)
        
        final_output = color_config['output_dir']
        consolidate_config = create_consolidation_config(color_config, regions, cwd, final_output)
        
        # Aguarda todos os jobs regionais desta cor
        dependency = ",".join(map(str, all_jobs[color]))
        
        if not args.dry_run:
            job_id = submit_slurm_job(sbatch_consolidate, consolidate_config, cwd, 
                                    aladin_cmd, max_mem, dependency)
            consolidate_jobs.append(job_id)
            print(f"  Consolidação submetida: {job_id}")
        else:
            print(f"  [DRY RUN] Consolidaria com dependência: {dependency}")
        
        final_outputs[f'in{color.capitalize()}'] = str(Path(cwd, final_output).absolute())
    
    # Job RGB final
    if consolidate_jobs:
        print(f"\n--- Job RGB Final ---")
        
        rgb_config = hips_runs['rgb'].copy()
        rgb_config.update(hips_config)
        rgb_config.update(final_outputs)
        
        rgb_config_path = cwd / "rgb_final.config"
        with open(rgb_config_path, 'w') as f:
            for key, value in rgb_config.items():
                if key.startswith('in'):  # inRed, inGreen, inBlue
                    f.write(f'{key}="{value}"\n')
                elif key == 'output_dir':
                    output_path = Path(cwd, value)
                    output_path.mkdir(exist_ok=True)
                    f.write(f'out="{output_path.absolute()}"\n')
                else:
                    f.write(f'{key}="{value}"\n')
        
        dependency = ",".join(map(str, consolidate_jobs))
        
        if not args.dry_run:
            final_job_id = submit_slurm_job("rgb.sbatch", rgb_config_path, cwd,
                                          aladin_cmd, max_mem, dependency)
            print(f"  RGB final submetido: {final_job_id}")
        else:
            print(f"  [DRY RUN] RGB final com dependência: {dependency}")
    
    print(f"\n✓ Paralelização configurada com {len(regions)} regiões por cor!")
    return 0


if __name__ == '__main__':
    exit(main())