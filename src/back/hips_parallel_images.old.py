#!/usr/bin/env python3
"""
Script para paralelização do HipsGen com imagens FITS por banda.
Cada imagem FITS é processada como uma região separada em paralelo.
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from astropy.io import fits
from astropy.wcs import WCS
import argparse
import subprocess
from yaml import safe_load
from glob import glob
import re


def find_fits_images(pattern: str, band_patterns: Dict[str, str] = None) -> Dict[str, List[Path]]:
    """
    Encontra imagens FITS organizadas por banda
    
    Args:
        pattern: Padrão glob para encontrar arquivos FITS
        band_patterns: Dicionário com padrões específicos por banda
        
    Returns:
        Dict com listas de arquivos por banda: {'g': [files], 'r': [files], 'i': [files]}
    """
    if band_patterns is None:
        # Padrões padrão para detectar bandas no nome do arquivo
        band_patterns = {
            'g': r'.*[_-]g[_-].*\.fits?$|.*[_-]g\.fits?$|.*_g_band.*\.fits?$|.*/g/.*[0-9].fits$',
            'r': r'.*[_-]r[_-].*\.fits?$|.*[_-]r\.fits?$|.*_r_band.*\.fits?$|.*/r/.*[0-9].fits$',
            'i': r'.*[_-]i[_-].*\.fits?$|.*[_-]i\.fits?$|.*_i_band.*\.fits?$|.*/i/.*[0-9].fits$'
        }
    
    # Encontra todos os arquivos FITS
    all_fits = glob(pattern, recursive=True)
    all_fits = [Path(f) for f in sorted(all_fits)]
    
    print(f"Encontradas {len(all_fits)} imagens FITS:")
    
    # Organiza por banda
    images_by_band = {'g': [], 'r': [], 'i': []}
    unmatched = []
    
    for fits_file in all_fits:
        # filename = fits_file.name.lower()
        filename = str(fits_file)
        matched = False
        
        for band, pattern_regex in band_patterns.items():
            print(filename)
            print(pattern_regex)
            if re.match(pattern_regex, filename, re.IGNORECASE):
                images_by_band[band].append(fits_file)
                matched = True
                break
        
        if not matched:
            unmatched.append(fits_file)
    
    # Relatório
    for band in ['g', 'r', 'i']:
        print(f"  Banda {band}: {len(images_by_band[band])} imagens")
        for img in images_by_band[band][:5]:  # Mostra primeiras 5
            print(f"    {img}")
        if len(images_by_band[band]) > 5:
            print(f"    ... e mais {len(images_by_band[band]) - 5}")
    
    if unmatched:
        print(f"  Não classificadas: {len(unmatched)}")
        for img in unmatched[:3]:
            print(f"    {img}")
        if len(unmatched) > 3:
            print(f"    ... e mais {len(unmatched) - 3}")
    
    return images_by_band


def extract_region_from_fits_header(fits_file: Path) -> Optional[Tuple[float, float, float, float]]:
    """
    Extrai região (RA/DEC min/max) do header WCS da imagem FITS
    
    Args:
        fits_file: Caminho para arquivo FITS
        
    Returns:
        Tupla (ra_min, ra_max, dec_min, dec_max) ou None se não conseguir extrair
    """
    try:
        with fits.open(fits_file) as hdul:
            # Procura por uma extensão com WCS válido
            for hdu in hdul:
                if hdu.data is not None and hdu.header:
                    try:
                        wcs = WCS(hdu.header)
                        if wcs.has_celestial:
                            # Calcula cantos da imagem
                            ny, nx = hdu.data.shape[-2:]  # Últimas 2 dimensões
                            corners_pix = np.array([
                                [0, 0],           # canto inferior esquerdo
                                [nx-1, 0],        # canto inferior direito  
                                [0, ny-1],        # canto superior esquerdo
                                [nx-1, ny-1]      # canto superior direito
                            ])
                            
                            # Converte para coordenadas celestes
                            corners_world = wcs.pixel_to_world_values(corners_pix)
                            
                            # Verifica se o resultado é uma tupla ou array
                            if isinstance(corners_world, tuple) and len(corners_world) == 2:
                                # Resultado como tupla (ra_array, dec_array)
                                ra_coords = np.array(corners_world[0])
                                dec_coords = np.array(corners_world[1])
                            elif hasattr(corners_world, 'shape') and len(corners_world.shape) == 2:
                                # Resultado como array 2D
                                ra_coords = corners_world[:, 0]
                                dec_coords = corners_world[:, 1]
                            else:
                                # Fallback: assume formato simples
                                ra_coords = np.array([c[0] for c in corners_world])
                                dec_coords = np.array([c[1] for c in corners_world])
                            
                            ra_min, ra_max = float(np.min(ra_coords)), float(np.max(ra_coords))
                            dec_min, dec_max = float(np.min(dec_coords)), float(np.max(dec_coords))
                            
                            return ra_min, ra_max, dec_min, dec_max
                    except Exception as e:
                        continue
                        
    except Exception as e:
        print(f"  Erro ao ler WCS de {fits_file}: {e}")
        return None
    
    return None


def extract_image_id_from_filename(fits_file: Path, id_pattern: str = "auto") -> str:
    """
    Extrai ID único da imagem baseado no nome do arquivo
    
    Args:
        fits_file: Caminho da imagem
        id_pattern: Padrão para extrair ID
        
    Returns:
        ID único da imagem
    """
    if id_pattern == "auto":
        # Remove extensão e caracteres problemáticos
        return fits_file.stem.replace(".", "_").replace("-", "_").replace(" ", "_")
    elif id_pattern == "tile":
        # Para imagens com padrão tile_XXXX
        match = re.search(r'tile[_-]?(\d+)', fits_file.name, re.IGNORECASE)
        if match:
            return f"tile_{match.group(1)}"
    elif id_pattern == "coords":
        # Para imagens com coordenadas no nome
        match = re.search(r'(\d+\.?\d*)[_-](\d+\.?\d*)', fits_file.stem)
        if match:
            return f"coord_{match.group(1)}_{match.group(2)}"
    
    # Fallback
    return fits_file.stem.replace(".", "_").replace("-", "_")


def create_config_for_image(base_config: Dict, fits_file: Path, image_id: str, 
                           output_dir: Path, region_bounds: Optional[Tuple] = None) -> Path:
    """
    Cria arquivo de configuração para uma imagem específica
    
    Args:
        base_config: Configuração base do HipsGen
        fits_file: Caminho da imagem FITS
        image_id: ID único desta imagem
        output_dir: Diretório de trabalho
        region_bounds: Limites opcionais da região
        
    Returns:
        Caminho do arquivo de configuração criado
    """
    config_name = f"{image_id}.config"
    config_path = output_dir / config_name
    
    with open(config_path, 'w') as f:
        # Copia parâmetros base
        for key, value in base_config.items():
            if key == 'input_dir':
                # Input é o diretório que contém esta imagem
                input_path = fits_file.parent.absolute()
                f.write(f'in="{input_path}"\n')
            elif key == 'output_dir':
                # Output específico para esta imagem
                output_path = output_dir / f"{value}_{image_id}"
                output_path.mkdir(parents=True, exist_ok=True)
                f.write(f'out="{output_path.absolute()}"\n')
            elif key == 'cache':
                # Cache específico por imagem
                cache_path = output_dir / f"{value}_{image_id}"
                cache_path.mkdir(parents=True, exist_ok=True)
                f.write(f'cache="{cache_path.absolute()}"\n')
            else:
                f.write(f'{key}="{value}"\n')
        
        # Se temos os limites da imagem, adiciona como region
        if region_bounds:
            ra_min, ra_max, dec_min, dec_max = region_bounds
            f.write(f'region="{ra_min},{dec_min},{ra_max},{dec_max}"\n')
    
    return config_path


def create_consolidation_config(base_config: Dict, image_outputs: List[str], 
                              output_dir: Path, final_output: str) -> Path:
    """Cria configuração para consolidação de todas as imagens de uma banda"""
    config_path = output_dir / f"consolidate_{final_output}.config"
    
    with open(config_path, 'w') as f:
        # Múltiplos inputs das imagens
        f.write(f'in="{",".join(image_outputs)}"\n')
        
        # Output final consolidado
        final_path = output_dir / final_output
        final_path.mkdir(parents=True, exist_ok=True)
        f.write(f'out="{final_path.absolute()}"\n')
        
        # Outros parâmetros
        for key, value in base_config.items():
            if key not in ['input_dir', 'output_dir', 'cache']:
                f.write(f'{key}="{value}"\n')
    
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


def main():
    parser = argparse.ArgumentParser(description='HipsGen com imagens FITS por banda')
    parser.add_argument('config_file', help='Arquivo de configuração YAML')
    parser.add_argument('images_pattern', help='Padrão glob para encontrar imagens FITS')
    parser.add_argument('--id-pattern', default='auto', choices=['auto', 'tile', 'coords'], 
                       help='Padrão para extrair ID da imagem')
    parser.add_argument('--max-images', type=int, help='Máximo de imagens por banda a processar')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simula, não submete jobs')
    parser.add_argument('--extract-regions', action='store_true', help='Extrai região WCS de cada imagem')
    parser.add_argument('--band-g', help='Padrão regex para banda G')
    parser.add_argument('--band-r', help='Padrão regex para banda R') 
    parser.add_argument('--band-i', help='Padrão regex para banda I')
    
    args = parser.parse_args()
    
    # Lê configuração
    with open(args.config_file, 'r') as f:
        config = safe_load(f)
    
    # Padrões de banda personalizados
    band_patterns = {}
    if args.band_g:
        band_patterns['g'] = args.band_g
    if args.band_r:
        band_patterns['r'] = args.band_r
    if args.band_i:
        band_patterns['i'] = args.band_i
    
    # Encontra imagens organizadas por banda
    images_by_band = find_fits_images(args.images_pattern, band_patterns if band_patterns else None)
    
    # Verifica se encontrou imagens
    total_images = sum(len(images) for images in images_by_band.values())
    if total_images == 0:
        print("Nenhuma imagem FITS encontrada!")
        return 1
    
    # Limita número de imagens se especificado
    if args.max_images:
        for band in images_by_band:
            if len(images_by_band[band]) > args.max_images:
                images_by_band[band] = images_by_band[band][:args.max_images]
                print(f"Banda {band}: processando apenas as primeiras {args.max_images} imagens")
   
    print('images_by_band')
    print(images_by_band)

    # Configurações
    cwd = Path(config.get("cwd", "."))
    cwd.mkdir(exist_ok=True)
    aladin_cmd = config.get("aladin_cmd", "Aladin.jar")
    max_mem = str(config.get("max_mem", "4"))
    
    hips_config = config['hipsgen']
    hips_runs = hips_config['runs']
    
    # Mapeamento de bandas para cores
    band_to_color = {'g': 'blue', 'r': 'green', 'i': 'red'}
    
    print(f"\n=== Processando imagens por banda ===")
    
    all_jobs = {}  # {color: [job_ids]}
    image_outputs = {color: [] for color in ['red', 'green', 'blue']}
    
    # Para cada banda
    for band, color in band_to_color.items():
        images = images_by_band[band]
        if not images:
            print(f"\nBanda {band} ({color}): Nenhuma imagem encontrada")
            continue
            
        print(f"\n--- Processando banda {band} ({color}): {len(images)} imagens ---")
        
        color_config = hips_runs[color].copy()
        color_config.update(hips_config)
        
        image_jobs = []
        
        # Job por imagem
        for fits_file in images:
            image_id = extract_image_id_from_filename(fits_file, args.id_pattern)
            
            # Extrai região da imagem se solicitado
            region_bounds = None
            if args.extract_regions:
                region_bounds = extract_region_from_fits_header(fits_file)
                if region_bounds:
                    ra_min, ra_max, dec_min, dec_max = region_bounds
                    print(f"  {image_id}: RA[{ra_min:.4f},{ra_max:.4f}] DEC[{dec_min:.4f},{dec_max:.4f}]")
                else:
                    print(f"  {image_id}: Não foi possível extrair região WCS")
            
            config_file = create_config_for_image(
                color_config, fits_file, image_id, cwd, region_bounds
            )
            
            # Registra output desta imagem
            image_output = str((cwd / f"{color_config['output_dir']}_{image_id}").absolute())
            image_outputs[color].append(image_output)
            
            print(f"  {image_id}: config={config_file.name}")
            
            if not args.dry_run:
                job_id = submit_slurm_job("color.sbatch", config_file, cwd, aladin_cmd, max_mem)
                image_jobs.append(job_id)
                print(f"    Job submetido: {job_id}")
            else:
                print(f"    [DRY RUN] Submeteria job para {image_id}: {config_file} - {cwd}")
        
        all_jobs[color] = image_jobs
    
    # Jobs de consolidação por cor  
    consolidate_jobs = []
    final_outputs = {}
    
    for color in ['red', 'green', 'blue']:
        if not all_jobs.get(color):
            continue
            
        print(f"\n--- Consolidação da cor: {color} ---")
        
        color_config = hips_runs[color].copy()
        color_config.update(hips_config)
        
        final_output = color_config['output_dir']
        print("FINAL_OUT: ", final_output)
        consolidate_config = create_consolidation_config(
            color_config, image_outputs[color], cwd, final_output
        )
        
        # Aguarda todos os jobs de imagem desta cor
        dependency = ",".join(map(str, all_jobs[color]))
        
        if not args.dry_run:
            job_id = submit_slurm_job("consolidate.sbatch", consolidate_config, cwd,
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
    
    total_processed = sum(len(images_by_band[band]) for band in ['g', 'r', 'i'])
    print(f"\n✓ Paralelização configurada para {total_processed} imagens!")
    return 0


if __name__ == '__main__':
    exit(main())
