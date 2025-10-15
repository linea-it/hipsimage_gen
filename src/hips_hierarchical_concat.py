#!/usr/bin/env python3
"""
Script para paralelização do HipsGen com concatenação hierárquica.

FLUXO DE PROCESSAMENTO:
1. Encontra arquivos particionados
2. Para cada cor (red, green, blue):
   - Executa HipsGen para cada partição em paralelo
   - Concatena hierarquicamente em pares até sobrar uma imagem
3. Consolida as 3 bandas finais em RGB

EXEMPLO COM 7 PARTIÇÕES:
  Nível 0: [P1] [P2] [P3] [P4] [P5] [P6] [P7]
  Nível 1: [P1+P2] [P3+P4] [P5+P6] [P7] ← P7 passa direto
  Nível 2: [P1234] [P567] 
  Nível 3: [P1234567] ← Resultado final por banda
"""

import argparse
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from glob import glob
from yaml import safe_load
import re


# ============================================================================
# SEÇÃO 1: DESCOBERTA DE ARQUIVOS
# ============================================================================

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

def find_fits_images(
    pattern: str, band_patterns: Dict[str, str] = None
) -> Dict[str, List[Path]]:
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
    images_by_band = {"g": [], "r": [], "i": []}
    unmatched = []

    for fits_file in all_fits:
        # filename = fits_file.name.lower()
        filename = str(fits_file)
        matched = False

        for band, pattern_regex in band_patterns.items():
            if re.match(pattern_regex, filename, re.IGNORECASE):
                images_by_band[band].append(fits_file)
                matched = True
                break

        if not matched:
            unmatched.append(fits_file)

    # Relatório
    for band in ["g", "r", "i"]:
        print(f"  Banda {band}: {len(images_by_band[band])} imagens")
        for img in images_by_band[band][:5]:  # Mostra primeiras 5
            print(f"    {img}")

    if unmatched:
        print(f"  Não classificadas: {len(unmatched)}")
        for img in unmatched[:3]:
            print(f"    {img}")
        if len(unmatched) > 3:
            print(f"    ... e mais {len(unmatched) - 3}")

    return images_by_band


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
                    npix = (
                        part.stem.split("=")[1] if "." in part else part.split("=")[1]
                    )

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


def create_partition_config(
    base_config: Dict,
    file_path: Path,
    region_id: str,
    output_dir: Path,
    bounds: Optional[Tuple] = None,
) -> Path:
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

    with open(config_path, "w") as f:
        # Copia parâmetros base
        for key, value in base_config.items():
            if key == "input_dir":
                # Input é o diretório que contém este arquivo específico
                input_path = file_path.absolute()
                f.write(f'in="{input_path}"\n')
            elif key == "output_dir":
                # Output específico para esta partição
                output_path = output_dir / f"{region_id}"
                output_path.mkdir(parents=True, exist_ok=True)
                f.write(f'out="{output_path.absolute()}"\n')
            elif key == "cache":
                # Cache específico por partição
                cache_path = output_dir / f"cache/{region_id}"
                cache_path.mkdir(parents=True, exist_ok=True)
                f.write(f'cache="{cache_path.absolute()}"\n')
            elif key == "runs":
                continue
            else:
                f.write(f'{key}="{value}"\n')

        # Se temos os limites da partição, adiciona como region
        if bounds:
            ra_min, ra_max, dec_min, dec_max = bounds
            f.write(f'region="{ra_min},{dec_min},{ra_max},{dec_max}"\n')

    return config_path


def create_concat_config(
    base_config: Dict, input_dirs: List[str], output_dir: Path, level: int, pair_id: str
) -> Path:
    """
    Cria configuração para concatenação de um par de HiPS

    Args:
        base_config: Configuração base
        input_dirs: Lista de diretórios de entrada para concatenar
        output_dir: Diretório de trabalho
        level: Nível hierárquico da concatenação
        pair_id: ID do par sendo concatenado

    Returns:
        Caminho do arquivo de configuração criado
    """
    config_name = f"concat_level{level}_{pair_id}.config"
    config_path = output_dir / config_name

    with open(config_path, "w") as f:
        # Múltiplos inputs para concatenação
        # f.write(f'in="{",".join(input_dirs)}"\n')
        f.write(f'in="{input_dirs[0].absolute()}"\n')

        # Output do par concatenado
        # concat_output = output_dir / f"concat_level{level}_{pair_id}"
        # concat_output.mkdir(parents=True, exist_ok=True)
        # f.write(f'out="{concat_output.absolute()}"\n')
        f.write(f'out="{input_dirs[1].absolute()}"\n')

        # Outros parâmetros (sem região específica)
        for key, value in base_config.items():
            if key not in ["input_dir", "output_dir", "cache", "runs"]:
                f.write(f'{key}="{value}"\n')

        # Cache para concatenação
        cache_path = output_dir / f"cache/concat_level{level}_{pair_id}"
        cache_path.mkdir(parents=True, exist_ok=True)
        f.write(f'cache="{cache_path.absolute()}"\n')

    return config_path


def create_final_rgb_config(
    base_config: Dict, band_inputs: Dict[str, str], output_dir: Path
) -> Path:
    """
    Cria configuração para consolidação RGB final

    Args:
        base_config: Configuração base RGB
        band_inputs: Dict com paths das bandas finais {color: path}
        output_dir: Diretório de trabalho

    Returns:
        Caminho do arquivo de configuração criado
    """
    config_path = output_dir / "rgb_final.config"

    with open(config_path, "w") as f:
        # Inputs das bandas
        for color, path in band_inputs.items():
            f.write(f'in{color.capitalize()}="{path}"\n')

        # Output RGB final
        rgb_output = output_dir / "hips_rgb_final"
        rgb_output.mkdir(parents=True, exist_ok=True)
        f.write(f'out="{rgb_output.absolute()}"\n')

        # Parâmetros RGB específicos
        for key, value in base_config.items():
            if key not in ["inRed", "inGreen", "inBlue", "output_dir"]:
                f.write(f'{key}="{value}"\n')

    return config_path


def submit_slurm_job(
    sbatch_script: str,
    config_file: Path,
    work_dir: Path,
    aladin_jar: str,
    max_mem: str,
    dependency: Optional[str] = None,
) -> int:
    """Submete job no Slurm e retorna o job ID"""
    cmd = ["sbatch"]

    if dependency:
        cmd.extend(["--dependency", f"afterok:{dependency}"])

    cmd.extend([sbatch_script, max_mem, aladin_jar, str(config_file)])

    try:
        result = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True, check=True
        )
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


def group_into_pairs(items: List) -> List[List]:
    """
    Agrupa lista de items em pares, deixando item sozinho se número ímpar

    Args:
        items: Lista de items para agrupar

    Returns:
        Lista de pares (sublistas)
    """
    pairs = []
    for i in range(0, len(items), 2):
        if i + 1 < len(items):
            pairs.append([items[i], items[i + 1]])
        else:
            pairs.append([items[i]])  # Item sozinho
    return pairs


def execute_hierarchical_concatenation(
    partition_outputs: List[str],
    partition_jobs: List[int],
    base_config: Dict,
    color: str,
    work_dir: Path,
    aladin_jar: str,
    max_mem: str,
    dry_run: bool = False,
) -> Tuple[str, List[int]]:
    """
    Executa concatenação hierárquica em pares até restar uma saída

    Args:
        partition_outputs: Lista de diretórios de saída das partições
        base_config: Configuração base
        color: Cor sendo processada
        work_dir: Diretório de trabalho
        aladin_jar: Caminho para Aladin.jar
        max_mem: Memória máxima
        dry_run: Apenas simular

    Returns:
        Tupla (caminho_final, lista_de_job_ids)
    """
    current_level_outputs = partition_outputs.copy()
    all_job_ids = []
    level = 0

    print(f"\n--- Concatenação hierárquica para {color} ---")
    print(f"Iniciando com {len(current_level_outputs)} partições")

    while len(current_level_outputs) > 1:
        level += 1
        pairs = group_into_pairs(current_level_outputs)
        job_id_pairs = group_into_pairs(current_level_outputs)
        next_level_outputs = []
        level_job_ids = []

        print(f"  Nível {level}: {len(pairs)} concatenações")

        for pair_idx, pair in enumerate(pairs):
            if len(pair) == 1:
                # Item sozinho, passa direto para próximo nível
                next_level_outputs.append(pair[0])
                level_job_ids.append(job_id_pairs[0])
                print(f"    Par {pair_idx}: passagem direta de {Path(pair[0]).name}")
                continue

            pair_id = f"{color}_pair{pair_idx}"

            # Cria config para concatenação deste par
            concat_config = create_concat_config(
                base_config, pair, work_dir, level, pair_id
            )

            # Path da saída desta concatenação
            concat_output = str(pair[1])
            next_level_outputs.append(concat_output)

            print(
                f"    Par {pair_idx}: {Path(pair[0]).name} + {Path(pair[1]).name} → {Path(pair[1]).name}"
            )

            if not dry_run:
                # Submete job de concatenação
                dependency = ",".join(map(str, job_id_pairs)) if job_id_pairs else None
                job_id = submit_slurm_job(
                    "concat.sbatch",
                    concat_config,
                    work_dir,
                    aladin_jar,
                    max_mem,
                    dependency,
                )
                level_job_ids.append(job_id)
                print(f"      Job submetido: {job_id}")
            else:
                print(f"      [DRY RUN] Concatenaria par {pair_idx}")
                print(f"      [DRY RUN] concat.sbatch {concat_config} {work_dir}")

        current_level_outputs = next_level_outputs
        all_job_ids.extend(level_job_ids)

        if level_job_ids:
            # Próximo nível depende dos jobs deste nível
            # (implementação simplificada - na prática, seria mais complexo)
            pass

    final_output = current_level_outputs[0]
    print(f"  Resultado final: {Path(final_output).name}")

    return final_output, all_job_ids


def main():
    parser = argparse.ArgumentParser(description="HipsGen com concatenação hierárquica")
    parser.add_argument("config_file", help="Arquivo de configuração YAML")
    parser.add_argument(
        "images_pattern",
        help='Padrão glob para encontrar arquivos (ex: "data/*/*.parquet")',
    )
    parser.add_argument("--ra-col", default="ra", help="Nome da coluna RA")
    parser.add_argument("--dec-col", default="dec", help="Nome da coluna DEC")
    parser.add_argument(
        "--id-pattern",
        default="auto",
        choices=["auto", "healpix", "custom"],
        help="Padrão para extrair ID da região",
    )
    parser.add_argument(
        "--max-images", type=int, help="Máximo de partições a processar"
    )
    parser.add_argument("--band-g", help="Padrão regex para banda G")
    parser.add_argument("--band-r", help="Padrão regex para banda R")
    parser.add_argument("--band-i", help="Padrão regex para banda I")

    parser.add_argument(
        "--dry-run", action="store_true", help="Apenas simula, não submete jobs"
    )

    args = parser.parse_args()

    """
    # Lê configuração
    with open(args.config_file, "r") as f:
        config = safe_load(f)

    # Encontra arquivos particionados
    # partition_files = find_partitioned_files(args.input_pattern)
    partition_files = find_fits_images(args.input_pattern)


    if not partition_files:
        print("Nenhum arquivo encontrado com o padrão especificado!")
        return 1

    # Limita número de partições se especificado
    if args.max_partitions:
        partition_files = partition_files[: args.max_partitions]
        print(f"Processando apenas as primeiras {len(partition_files)} partições")
    """


    # Lê configuração
    with open(args.config_file, "r", encoding="utf-8") as f:
        config = safe_load(f)

    # Padrões de banda personalizados
    band_patterns = {}
    if args.band_g:
        band_patterns["g"] = args.band_g
    if args.band_r:
        band_patterns["r"] = args.band_r
    if args.band_i:
        band_patterns["i"] = args.band_i

    # Encontra imagens organizadas por banda
    images_by_band = find_fits_images(
        args.images_pattern, band_patterns if band_patterns else None
    )

    # Verifica se encontrou imagens
    total_images = sum(len(images) for images in images_by_band.values())
    if total_images == 0:
        print("Nenhuma imagem FITS encontrada!")
        return 1

    # Limita número de imagens se especificado
    if args.max_images:
        for band in images_by_band:
            if len(images_by_band[band]) > args.max_images:
                images_by_band[band] = images_by_band[band][: args.max_images]
                print(
                    f"Banda {band}: processando apenas as primeiras {args.max_images} imagens"
                )


    # Configurações
    cwd = Path(config.get("cwd", "."))
    cwd.mkdir(exist_ok=True)
    aladin_cmd = config.get("aladin_cmd", "Aladin.jar")
    max_mem = str(config.get("max_mem", "2"))

    hips_config = config["hipsgen"]
    hips_runs = hips_config["runs"]


    # Para cada cor
    colors = ["red", "green", "blue"]
    all_partition_jobs = {}  # {color: [job_ids]}
    all_concat_jobs = {}  # {color: [job_ids]}
    final_band_outputs = {}  # {color: path}

    # Mapeamento de bandas para cores
    band_to_color = {"g": "blue", "r": "green", "i": "red"}

    print("\n=== Processando imagens por banda ===")


    # Fase 1: Executa HipsGen para cada partição
    for band, color in band_to_color.items():
        print(f"\n--- Fase 1: Processando partições da cor {color} ---")

        
        partition_jobs = []
        partition_outputs = []

        images = images_by_band[band]

        if not images:
            print(f"\nBanda {band} ({color}): Nenhuma imagem encontrada")
            continue

        color_config = hips_runs[color].copy()
        color_config.update(hips_config)


        # Job por image + cor
        for partition_file in images:
            region_id = extract_region_id_from_filename(partition_file, color, args.id_pattern)

            config_file = create_partition_config(
                color_config, partition_file, region_id, cwd
            )

            # Registra output desta partição
            partition_output = str((cwd / f"{region_id}").absolute())
            partition_outputs.append(partition_output)

            print(f"  Partição {region_id}: config={config_file.name}")

            if not args.dry_run:
                job_id = submit_slurm_job(
                    "color.sbatch", config_file, cwd, aladin_cmd, max_mem
                )
                partition_jobs.append(job_id)
                print(f"    Job submetido: {job_id}")
            else:
                partition_jobs.append(region_id)
                print(f"    [DRY RUN] Submeteria job para {region_id}")
                print(f"    [DRY RUN] color.sbatch {config_file} {cwd}")

        all_partition_jobs[color] = partition_jobs


        print('jobs: ', partition_jobs)
        print('outputs: ', partition_outputs)

        exit(0)

        # Fase 2: Concatenação hierárquica para esta cor
        if partition_outputs:
            final_output, concat_jobs = execute_hierarchical_concatenation(
                partition_outputs,
                partition_jobs,
                color_config,
                color,
                cwd,
                aladin_cmd,
                max_mem,
                args.dry_run,
            )

            all_concat_jobs[color] = concat_jobs
            final_band_outputs[color] = final_output

    # Fase 3: RGB final
    if final_band_outputs:
        print("\n--- Fase 3: Consolidação RGB Final ---")

        rgb_config = hips_runs["rgb"].copy()
        rgb_config.update(hips_config)

        rgb_config_file = create_final_rgb_config(rgb_config, final_band_outputs, cwd)

        # Aguarda todos os jobs de concatenação
        all_dependencies = []
        for color_jobs in all_concat_jobs.values():
            all_dependencies.extend(color_jobs)

        dependency = ",".join(map(str, all_dependencies)) if all_dependencies else None

        if not args.dry_run and all_dependencies:
            final_job_id = submit_slurm_job(
                "rgb.sbatch", rgb_config_file, cwd, aladin_cmd, max_mem, dependency
            )
            print(f"  RGB final submetido: {final_job_id}")
        else:
            print(f"  [DRY RUN] RGB final com dependência: {dependency}")
            print(f"  [DRY RUN] rgb.sbatch {rgb_config_file} {cwd}")

    print(
        f"  - {sum(len(jobs) for jobs in all_partition_jobs.values())} jobs de partição"
    )
    print(
        f"  - {sum(len(jobs) for jobs in all_concat_jobs.values())} jobs de concatenação"
    )
    print("  - 1 job RGB final")

    return 0


if __name__ == "__main__":
    exit(main())
