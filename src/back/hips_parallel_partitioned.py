#!/usr/bin/env python3
"""
Script para paralelização do HipsGen quando os dados fotométricos
já estão particionados espacialmente (ex: por HEALPix, tiles, etc.)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from astropy.io import fits
import argparse
import subprocess
from yaml import safe_load
from glob import glob


def find_partitioned_files(input_pattern: str) -> List[Path]:
    """
    Encontra arquivos de dados particionados usando padrão glob
    
    Args:
        input_pattern: Padrão para encontrar arquivos (ex: "data/*/Npix=*.parquet")
        
    Returns:
        Lista de caminhos dos arquivos encontrados
    """
    files = glob(input_pattern, recursive=True)
    file_paths = [Path(f) for f in sorted(files)]
    
    print(f"Encontrados {len(file_paths)} arquivos particionados:")
    for i, fp in enumerate(file_paths[:10]):  # Mostra primeiros 10
        print(f"  {i+1}: {fp}")
    
    if len(file_paths) > 10:
        print(f"  ... e mais {len(file_paths) - 10} arquivos")
    
    return file_paths


def extract_region_id_from_filename(file_path: Path, color: str, id_pattern: str = "auto") -> str:
    """
    Extrai ID da região do nome do arquivo
    
    Args:
        file_path: Caminho do arquivo
        id_pattern: Padrão para extrair ID ("auto", "healpix", "custom")
        
    Returns:
        ID único da região
    """
    if id_pattern == "healpix":
        # Para arquivos HEALPix: Norder=X/Dir=Y/Npix=Z.ext
        name = str(file_path)
        if "Npix=" in name:
            parts = name.split("/")
            norder = dec = npix = None
            
            for part in parts:
                if part.startswith("Norder="):
                    norder = part.split("=")[1]
                elif part.startswith("Dir="):
                    dec = part.split("=")[1]  
                elif part.startswith("Npix="):
                    npix = part.stem.split("=")[1] if "." in part else part.split("=")[1]
            
            if norder and dec and npix:
                return f"healpix_n{norder}_d{dec}_p{npix}"
    
    elif id_pattern == "auto":
        # Usa o nome do arquivo (sem extensão) como ID
        return f'{color}.{file_path.stem.replace(".", "_").replace("-", "_").replace(",", "_")}'

    
    else:
        # Pattern customizado - por enquanto igual ao auto
        return f'{color}.{file_path.stem.replace(".", "_").replace("-", "_").replace(",", "_")}'
    
    # Fallback: usa o nome completo
    return str(file_path.name).replace(".", "_").replace("-", "_")


def get_bounds_from_partitioned_data(file_paths: List[Path], ra_col: str = 'ra', 
                                    dec_col: str = 'dec') -> Tuple[float, float, float, float]:
    """
    Extrai os limites globais de múltiplos arquivos particionados
    Otimizado para não carregar todos os dados na memória
    """
    print("Analisando limites dos dados particionados...")
    
    ra_min_global = float('inf')
    ra_max_global = float('-inf')
    dec_min_global = float('inf') 
    dec_max_global = float('-inf')
    total_objects = 0
    
    for i, file_path in enumerate(file_paths):
        try:
            # Lê apenas as colunas necessárias
            if file_path.suffix.lower() in ['.parquet', '.pq']:
                df = pd.read_parquet(file_path, columns=[ra_col, dec_col])
            elif file_path.suffix.lower() in ['.fits', '.fit']:
                with fits.open(file_path) as hdul:
                    for hdu in hdul:
                        if hasattr(hdu, 'data') and hdu.data is not None:
                            if hasattr(hdu.data, 'dtype') and len(hdu.data.dtype) > 0:
                                if ra_col in hdu.data.dtype.names and dec_col in hdu.data.dtype.names:
                                    df = pd.DataFrame({
                                        ra_col: hdu.data[ra_col],
                                        dec_col: hdu.data[dec_col]
                                    })
                                    break
            else:
                print(f"  Pulando arquivo não suportado: {file_path}")
                continue
            
            # Remove valores inválidos
            valid_mask = pd.notna(df[ra_col]) & pd.notna(df[dec_col])
            df_clean = df[valid_mask]
            
            if len(df_clean) == 0:
                print(f"  Arquivo {i+1}: VAZIO")
                continue
            
            # Atualiza limites globais
            ra_min = float(df_clean[ra_col].min())
            ra_max = float(df_clean[ra_col].max())
            dec_min = float(df_clean[dec_col].min()) 
            dec_max = float(df_clean[dec_col].max())
            
            ra_min_global = min(ra_min_global, ra_min)
            ra_max_global = max(ra_max_global, ra_max)
            dec_min_global = min(dec_min_global, dec_min)
            dec_max_global = max(dec_max_global, dec_max)
            
            total_objects += len(df_clean)
            
            print(f"  Arquivo {i+1}/{len(file_paths)}: {len(df_clean)} objetos, "
                  f"RA[{ra_min:.3f},{ra_max:.3f}] DEC[{dec_min:.3f},{dec_max:.3f}]")
            
        except Exception as e:
            print(f"  Erro no arquivo {file_path}: {e}")
            continue
    
    print(f"\nLimites globais: RA[{ra_min_global:.4f},{ra_max_global:.4f}] "
          f"DEC[{dec_min_global:.4f},{dec_max_global:.4f}]")
    print(f"Total de objetos: {total_objects}")
    
    return ra_min_global, ra_max_global, dec_min_global, dec_max_global


def create_config_for_partition(base_config: Dict, file_path: Path, region_id: str, 
                               output_dir: Path, bounds: Optional[Tuple] = None) -> Path:
    """
    Cria arquivo de configuração para uma partição específica
    
    Args:
        base_config: Configuração base do HipsGen
        file_path: Caminho do arquivo de dados desta partição
        region_id: ID único desta região/partição
        output_dir: Diretório de trabalho
        bounds: Limites opcionais (ra_min, ra_max, dec_min, dec_max)
        
    Returns:
        Caminho do arquivo de configuração criado
    """
    config_name = f"{region_id}.config"
    config_path = output_dir / config_name
    
    with open(config_path, 'w') as f:
        # Copia parâmetros base
        for key, value in base_config.items():
            if key == 'input_dir':
                # Input é o diretório que contém este arquivo específico
                input_path = file_path.absolute()
                f.write(f'in="{input_path}"\n')
            elif key == 'output_dir':
                # Output específico para esta partição
                output_path = output_dir / f"{value}_{region_id}"
                output_path.mkdir(parents=True, exist_ok=True)
                f.write(f'out="{output_path.absolute()}"\n')
            elif key == 'cache':
                # Cache específico por partição
                cache_path = output_dir / f"{value}_{region_id}"
                cache_path.mkdir(parents=True, exist_ok=True)
                f.write(f'cache="{cache_path.absolute()}"\n')
            else:
                f.write(f'{key}="{value}"\n')
        
        # Se temos os limites da partição, adiciona como region
        if bounds:
            ra_min, ra_max, dec_min, dec_max = bounds
            f.write(f'region="{ra_min},{dec_min},{ra_max},{dec_max}"\n')
    
    return config_path


def submit_slurm_job(sbatch_script: str, config_file: Path, work_dir: Path,
                    aladin_jar: str, max_mem: str, dependency: Optional[str] = None) -> int:
    """Submete job no Slurm e retorna o job ID"""
    cmd = ["sbatch"]
    
    if dependency:
        cmd.extend(["--dependency", f"afterok:{dependency}"])
    
    cmd.extend([sbatch_script, max_mem, aladin_jar, str(config_file)])
    
    try:
        result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True, check=True)
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


def create_consolidation_config(base_config: Dict, partition_outputs: List[str], 
                              output_dir: Path, final_output: str) -> Path:
    """Cria configuração para consolidação de todas as partições"""
    config_path = output_dir / f"consolidate_{final_output}.config"
    
    with open(config_path, 'w') as f:
        # Múltiplos inputs das partições
        f.write(f'in="{",".join(partition_outputs)}"\n')
        
        # Output final consolidado
        final_path = output_dir / final_output
        final_path.mkdir(parents=True, exist_ok=True)
        f.write(f'out="{final_path.absolute()}"\n')
        
        # Outros parâmetros (sem região específica)
        for key, value in base_config.items():
            if key not in ['input_dir', 'output_dir', 'cache']:
                f.write(f'{key}="{value}"\n')
    
    return config_path


def main():
    parser = argparse.ArgumentParser(description='HipsGen com dados já particionados espacialmente')
    parser.add_argument('config_file', help='Arquivo de configuração YAML')
    parser.add_argument('input_pattern', help='Padrão glob para encontrar arquivos (ex: "data/*/*.parquet")')
    parser.add_argument('--ra-col', default='ra', help='Nome da coluna RA')
    parser.add_argument('--dec-col', default='dec', help='Nome da coluna DEC')
    parser.add_argument('--id-pattern', default='auto', choices=['auto', 'healpix', 'custom'], 
                       help='Padrão para extrair ID da região')
    parser.add_argument('--max-partitions', type=int, help='Máximo de partições a processar')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simula, não submete jobs')
    parser.add_argument('--extract-bounds', action='store_true', help='Extrai limites de cada partição')
    
    args = parser.parse_args()
    
    # Lê configuração
    with open(args.config_file, 'r') as f:
        config = safe_load(f)
    
    # Encontra arquivos particionados
    partition_files = find_partitioned_files(args.input_pattern)
    
    if not partition_files:
        print("Nenhum arquivo encontrado com o padrão especificado!")
        return 1
    
    # Limita número de partições se especificado
    if args.max_partitions:
        partition_files = partition_files[:args.max_partitions]
        print(f"Processando apenas as primeiras {len(partition_files)} partições")
    
    # Configurações
    cwd = Path(config.get("cwd", "."))
    cwd.mkdir(exist_ok=True)
    aladin_cmd = config.get("aladin_cmd", "Aladin.jar")
    max_mem = str(config.get("max_mem", "2"))
    
    hips_config = config['hipsgen']
    hips_runs = hips_config['runs']
    
    print(f"\n=== Processando {len(partition_files)} partições ===")
    
    # Para cada cor
    colors = ["red", "green", "blue"]
    all_jobs = {}  # {color: [job_ids]}
    partition_outputs = {color: [] for color in colors}  # Outputs por cor
    
    for color in colors:
        print(f"\n--- Processando cor: {color} ---")
        
        color_config = hips_runs[color].copy()
        color_config.update(hips_config)
        
        partition_jobs = []
        
        # Job por partição
        for partition_file in partition_files:
            region_id = extract_region_id_from_filename(partition_file, color, args.id_pattern)
            
            # Se solicitado, extrai limites específicos desta partição
            bounds = None
            if args.extract_bounds:
                try:
                    ra_min, ra_max, dec_min, dec_max = get_bounds_from_partitioned_data(
                        [partition_file], args.ra_col, args.dec_col
                    )
                    bounds = (ra_min, ra_max, dec_min, dec_max)
                except Exception as e:
                    print(f"  Aviso: Não foi possível extrair limites de {partition_file}: {e}")
            
            config_file = create_config_for_partition(
                color_config, partition_file, region_id, cwd, bounds
            )
            
            # Registra output desta partição
            partition_output = str((cwd / f"{color_config['output_dir']}_{region_id}").absolute())
            partition_outputs[color].append(partition_output)
            
            print(f"  Partição {region_id}: config={config_file.name}")
            
            if not args.dry_run:
                job_id = submit_slurm_job("color.sbatch", config_file, cwd, aladin_cmd, max_mem)
                partition_jobs.append(job_id)
                print(f"    Job submetido: {job_id}")
            else:
                print(f"    [DRY RUN] Submeteria job para {region_id}")
                print(f"    [DRY RUN] {cwd} {config_file}")
        
        all_jobs[color] = partition_jobs
    
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
        consolidate_config = create_consolidation_config(
            color_config, partition_outputs[color], cwd, final_output
        )
        
        # Aguarda todos os jobs de partição desta cor
        dependency = ",".join(map(str, all_jobs[color]))
        
        if not args.dry_run:
            job_id = submit_slurm_job("consolidate.sbatch", consolidate_config, cwd,
                                    aladin_cmd, max_mem, dependency)
            consolidate_jobs.append(job_id)
            print(f"  Consolidação submetida: {job_id}")
        else:
            print(f"  [DRY RUN] Consolidaria com dependência: {dependency}")
            print(f"  [DRY RUN] {cwd} {consolidate_config}")
        
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
            print(f"  [DRY RUN] {cwd} {rgb_config_path}")
    
    print(f"\n✓ Paralelização configurada para {len(partition_files)} partições!")
    return 0


if __name__ == '__main__':
    exit(main())
