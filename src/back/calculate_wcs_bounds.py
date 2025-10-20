#!/usr/bin/env python3
"""
Script para calcular os limites RA/DEC de uma imagem FITS a partir do WCS
"""

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
import argparse


def calculate_bounds_manual(crval_ra, crval_dec, crpix_x, crpix_y, cd11, cd12, cd21, cd22, naxis1, naxis2):
    """
    Calcula limites manualmente usando a transformação WCS
    
    Args:
        crval_ra, crval_dec: Coordenadas do pixel de referência (graus)
        crpix_x, crpix_y: Pixel de referência (1-indexed)
        cd11, cd12, cd21, cd22: Matriz CD (graus/pixel)
        naxis1, naxis2: Dimensões da imagem (pixels)
    
    Returns:
        (ra_min, ra_max, dec_min, dec_max)
    """
    print("=== Cálculo Manual ===")
    print(f"Centro (CRVAL): RA={crval_ra:.6f}°, DEC={crval_dec:.6f}°")
    print(f"Pixel referência (CRPIX): X={crpix_x}, Y={crpix_y}")
    print(f"Matriz CD: [{cd11:.2e}, {cd12:.2e}; {cd21:.2e}, {cd22:.2e}]")
    print(f"Dimensões: {naxis1} × {naxis2} pixels")
    
    # Cantos da imagem em pixels (0-indexed)
    corners_pix = np.array([
        [1, 1],                    # canto inferior esquerdo
        [naxis1, 1],               # canto inferior direito
        [1, naxis2],               # canto superior esquerdo  
        [naxis1, naxis2]           # canto superior direito
    ])
    
    print(f"\nCantos em pixels (1-indexed):")
    for i, (x, y) in enumerate(corners_pix):
        print(f"  Canto {i+1}: ({x}, {y})")
    
    # Conversão para coordenadas celestes
    ra_coords = []
    dec_coords = []
    
    for x_pix, y_pix in corners_pix:
        # Distância do pixel de referência
        dx = x_pix - crpix_x
        dy = y_pix - crpix_y
        
        # Transformação linear usando matriz CD
        delta_ra = cd11 * dx + cd12 * dy
        delta_dec = cd21 * dx + cd22 * dy
        
        # Coordenadas finais
        ra = crval_ra + delta_ra
        dec = crval_dec + delta_dec
        
        ra_coords.append(ra)
        dec_coords.append(dec)
        
        print(f"  Pixel ({x_pix}, {y_pix}) → RA={ra:.6f}°, DEC={dec:.6f}°")
    
    ra_min, ra_max = min(ra_coords), max(ra_coords)
    dec_min, dec_max = min(dec_coords), max(dec_coords)
    
    print(f"\nLimites calculados:")
    print(f"  RA: [{ra_min:.6f}°, {ra_max:.6f}°] (largura: {ra_max-ra_min:.6f}°)")
    print(f"  DEC: [{dec_min:.6f}°, {dec_max:.6f}°] (altura: {dec_max-dec_min:.6f}°)")
    
    return ra_min, ra_max, dec_min, dec_max


def calculate_bounds_astropy(fits_file):
    """
    Calcula limites usando AstroPy (método mais robusto)
    
    Args:
        fits_file: Caminho para arquivo FITS
        
    Returns:
        (ra_min, ra_max, dec_min, dec_max)
    """
    print(f"\n=== Cálculo com AstroPy ===")
    print(f"Arquivo: {fits_file}")
    
    with fits.open(fits_file) as hdul:
        for i, hdu in enumerate(hdul):
            if hdu.data is not None and hdu.header:
                try:
                    wcs = WCS(hdu.header)
                    if wcs.has_celestial:
                        print(f"Usando extensão {i}")
                        
                        # Dimensões da imagem
                        if len(hdu.data.shape) >= 2:
                            ny, nx = hdu.data.shape[-2:]  # Últimas 2 dimensões
                        else:
                            print("  Erro: dados não são 2D")
                            continue
                        
                        print(f"Dimensões detectadas: {nx} × {ny} pixels")
                        
                        # Cantos da imagem (0-indexed)
                        corners_pix = np.array([
                            [0, 0],           # canto inferior esquerdo
                            [nx-1, 0],        # canto inferior direito  
                            [0, ny-1],        # canto superior esquerdo
                            [nx-1, ny-1]      # canto superior direito
                        ])
                        
                        # Converte para coordenadas celestes
                        try:
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
                            
                            print(f"Cantos em coordenadas:")
                            for i, (ra, dec) in enumerate(zip(ra_coords, dec_coords)):
                                print(f"  Canto {i+1}: RA={ra:.6f}°, DEC={dec:.6f}°")
                            
                            ra_min, ra_max = float(np.min(ra_coords)), float(np.max(ra_coords))
                            dec_min, dec_max = float(np.min(dec_coords)), float(np.max(dec_coords))
                            
                            print(f"\nLimites calculados (AstroPy):")
                            print(f"  RA: [{ra_min:.6f}°, {ra_max:.6f}°] (largura: {ra_max-ra_min:.6f}°)")
                            print(f"  DEC: [{dec_min:.6f}°, {dec_max:.6f}°] (altura: {dec_max-dec_min:.6f}°)")
                            
                            return ra_min, ra_max, dec_min, dec_max
                            
                        except Exception as e:
                            print(f"  Erro na conversão: {e}")
                            continue
                            
                except Exception as e:
                    print(f"  Erro criando WCS: {e}")
                    continue
    
    print("Não foi possível extrair WCS válido")
    return None


def main():
    parser = argparse.ArgumentParser(description='Calcula limites RA/DEC de imagem FITS')
    parser.add_argument('--fits-file', help='Arquivo FITS para analisar')
    parser.add_argument('--manual', action='store_true', help='Usar dados do exemplo manual')
    
    args = parser.parse_args()
    
    if args.manual:
        # Dados do seu exemplo
        crval_ra = 58.4771573604061
        crval_dec = -36.4462809917355
        crpix_x = -9900.0
        crpix_y = -9900.0
        cd11 = -5.55555555555929e-05
        cd12 = 0.0
        cd21 = 0.0
        cd22 = 5.55555555555929e-05
        naxis1 = 4100
        naxis2 = 4100
        
        bounds = calculate_bounds_manual(
            crval_ra, crval_dec, crpix_x, crpix_y, 
            cd11, cd12, cd21, cd22, naxis1, naxis2
        )
        
        print(f"\n=== RESULTADO FINAL ===")
        print(f"RA range: {bounds[0]:.6f} to {bounds[1]:.6f}")
        print(f"DEC range: {bounds[2]:.6f} to {bounds[3]:.6f}")
        print(f"Region parameter: region=\"{bounds[0]},{bounds[2]},{bounds[1]},{bounds[3]}\"")
        
    elif args.fits_file:
        bounds = calculate_bounds_astropy(args.fits_file)
        if bounds:
            ra_min, ra_max, dec_min, dec_max = bounds
            print(f"\n=== RESULTADO FINAL ===")
            print(f"RA range: {ra_min:.6f} to {ra_max:.6f}")
            print(f"DEC range: {dec_min:.6f} to {dec_max:.6f}")
            print(f"Region parameter: region=\"{ra_min},{dec_min},{ra_max},{dec_max}\"")
    
    else:
        print("Use --manual para o exemplo ou --fits-file para analisar um arquivo")
        
        # Exemplo de uso
        print("\nExemplos:")
        print("  python calculate_wcs_bounds.py --manual")
        print("  python calculate_wcs_bounds.py --fits-file image.fits")


if __name__ == '__main__':
    main()