#!/usr/bin/env python3
"""
Script para descomprimir arquivos FITS GZIP para uso com HipsGen/Aladin
"""

from pathlib import Path
from astropy.io import fits
import argparse
import shutil
from typing import List
import numpy as np
from glob import glob


def is_compressed_fits(fits_file: Path) -> bool:
    """
    Verifica se um arquivo FITS está comprimido
    
    Args:
        fits_file: Caminho do arquivo FITS
        
    Returns:
        True se estiver comprimido
    """
    try:
        with fits.open(fits_file) as hdul:
            for hdu in hdul:
                if hasattr(hdu, 'header'):
                    # Verifica keywords de compressão
                    compression_keywords = ['ZCMPTYPE', 'ZBITPIX', 'ZNAXIS', 'ZQUANTIZ']
                    for keyword in compression_keywords:
                        if keyword in hdu.header:
                            return True
                            
                    # Verifica se é CompImageHDU (compressed)
                    if type(hdu).__name__ == 'CompImageHDU':
                        return True
        
        return False
        
    except Exception as e:
        print(f"Erro ao verificar compressão de {fits_file}: {e}")
        return False


def decompress_fits_file(input_file: Path, output_file: Path, extension: int = 1) -> bool:
    """
    Descomprime um arquivo FITS
    
    Args:
        input_file: Arquivo FITS comprimido
        output_file: Arquivo FITS descomprimido de saída
        extension: Extensão com os dados da imagem (padrão: 1 para LSST)
        
    Returns:
        True se bem sucedido
    """
    try:
        with fits.open(input_file) as hdul:
            # Encontra a extensão com dados de imagem
            image_hdu = None
            image_ext = None
            
            if extension < len(hdul):
                if hdul[extension].data is not None:
                    image_hdu = hdul[extension]
                    image_ext = extension
            
            if image_hdu is None:
                # Procura a primeira extensão com dados de imagem
                for i, hdu in enumerate(hdul):
                    if hdu.data is not None and len(hdu.data.shape) >= 2:
                        image_hdu = hdu
                        image_ext = i
                        break
            
            if image_hdu is None:
                print(f"  Erro: Nenhuma extensão de imagem encontrada em {input_file}")
                return False
            
            print(f"  Usando extensão {image_ext}: {image_hdu.data.shape}")
            
            # Cria novo HDU primário com os dados descomprimidos
            primary = fits.PrimaryHDU(data=image_hdu.data, header=image_hdu.header)
            
            # Remove keywords de compressão que podem causar problemas
            compression_keywords = [
                'ZCMPTYPE', 'ZBITPIX', 'ZNAXIS', 'ZNAXIS1', 'ZNAXIS2', 
                'ZQUANTIZ', 'ZDITHER0', 'ZBLANK', 'CHECKSUM', 'DATASUM'
            ]
            
            for keyword in compression_keywords:
                if keyword in primary.header:
                    del primary.header[keyword]
            
            # Força BITPIX correto baseado no tipo de dados
            if image_hdu.data.dtype == np.float32:
                primary.header['BITPIX'] = -32
            elif image_hdu.data.dtype == np.float64:
                primary.header['BITPIX'] = -64
            elif image_hdu.data.dtype == np.int32:
                primary.header['BITPIX'] = 32
            elif image_hdu.data.dtype == np.int16:
                primary.header['BITPIX'] = 16
            
            # Força NAXIS correto
            primary.header['NAXIS'] = len(image_hdu.data.shape)
            for i, size in enumerate(image_hdu.data.shape[::-1], 1):  # FITS usa ordem inversa
                primary.header[f'NAXIS{i}'] = size
            
            # Salva arquivo descomprimido
            hdul_out = fits.HDUList([primary])
            hdul_out.writeto(output_file, overwrite=True)
            
            print(f"  ✓ Descomprimido: {output_file}")
            return True
            
    except Exception as e:
        print(f"  Erro ao descomprimir {input_file}: {e}")
        return False


def decompress_fits_batch(input_pattern: str, output_dir: Path, 
                         dry_run: bool = False, extension: int = 1) -> List[Path]:
    """
    Descomprime múltiplos arquivos FITS
    
    Args:
        input_pattern: Padrão glob para encontrar arquivos
        output_dir: Diretório de saída
        dry_run: Apenas simula
        extension: Extensão com dados de imagem
        
    Returns:
        Lista de arquivos descomprimidos
    """
    # Encontra arquivos
    input_files = glob(input_pattern, recursive=True)
    input_files = [Path(f) for f in sorted(input_files)]
    
    print(f"Encontrados {len(input_files)} arquivos FITS:")
    
    if not input_files:
        print("Nenhum arquivo encontrado!")
        return []
    
    # Prepara diretório de saída
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    decompressed_files = []
    compressed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, input_file in enumerate(input_files):
        print(f"\n[{i+1}/{len(input_files)}] Processando: {input_file.name}")
        
        # Verifica se está comprimido
        if is_compressed_fits(input_file):
            compressed_count += 1
            print(f"  Status: Comprimido - precisa descomprimir")
            
            # Nome do arquivo de saída
            output_file = output_dir / f"{input_file.stem}_decompressed.fits"
            
            if dry_run:
                print(f"  [DRY RUN] Criaria: {output_file}")
                decompressed_files.append(output_file)
            else:
                if decompress_fits_file(input_file, output_file, extension):
                    decompressed_files.append(output_file)
                else:
                    error_count += 1
        else:
            skipped_count += 1
            print(f"  Status: Não comprimido - copiando diretamente")
            
            # Copia arquivo não comprimido
            output_file = output_dir / input_file.name
            
            if dry_run:
                print(f"  [DRY RUN] Copiaria: {output_file}")
                decompressed_files.append(output_file)
            else:
                try:
                    shutil.copy2(input_file, output_file)
                    decompressed_files.append(output_file)
                    print(f"  ✓ Copiado: {output_file}")
                except Exception as e:
                    print(f"  Erro ao copiar: {e}")
                    error_count += 1
    
    # Relatório final
    print(f"\n=== RELATÓRIO FINAL ===")
    print(f"Total processado: {len(input_files)}")
    print(f"Comprimidos (descomprimidos): {compressed_count}")
    print(f"Não comprimidos (copiados): {skipped_count}")
    print(f"Erros: {error_count}")
    print(f"Arquivos de saída criados: {len(decompressed_files)}")
    
    if not dry_run and decompressed_files:
        print(f"\nArquivos descomprimidos salvos em: {output_dir}")
        
        # Lista alguns arquivos de exemplo
        print("Primeiros arquivos criados:")
        for f in decompressed_files[:5]:
            print(f"  {f}")
        if len(decompressed_files) > 5:
            print(f"  ... e mais {len(decompressed_files) - 5}")
    
    return decompressed_files


def main():
    parser = argparse.ArgumentParser(description='Descomprime arquivos FITS para uso com HipsGen')
    parser.add_argument('input_pattern', help='Padrão glob para arquivos FITS (ex: "data/*.fits")')
    parser.add_argument('output_dir', help='Diretório para arquivos descomprimidos')
    parser.add_argument('--extension', type=int, default=1, 
                       help='Extensão com dados de imagem (padrão: 1 para LSST)')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simula, não processa')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    print(f"Descompressão de arquivos FITS")
    print(f"Padrão de entrada: {args.input_pattern}")
    print(f"Diretório de saída: {output_dir}")
    print(f"Extensão de imagem: {args.extension}")
    
    if args.dry_run:
        print("Modo DRY RUN - apenas simulação")
    
    # Processa arquivos
    decompressed_files = decompress_fits_batch(
        args.input_pattern, 
        output_dir, 
        args.dry_run, 
        args.extension
    )
    
    if decompressed_files:
        print(f"\n✓ Processamento concluído!")
        print(f"Agora você pode usar os arquivos em '{output_dir}' com o HipsGen")
    else:
        print(f"\n⚠ Nenhum arquivo processado")
    
    return 0


if __name__ == '__main__':
    exit(main())