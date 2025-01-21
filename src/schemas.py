from dataclasses import dataclass

@dataclass
class ColorConfig:
    input_dir: str = './input_%s'  
    output_dir: str = './output_%s'
    maxthread: str = '10'
    creator_did: str = 'CDS/P/LSST/DP0'
    hips_creator: str = 'LIneA'
    obs_title: str = 'LSST DP0'
    mode: str = 'mean'
    pixelcut: str = '-1.2 400 asinh'
    cache: str = './tmp'              

@dataclass
class RGBConfig:
    inRed: str = './input_r'
    inBlue: str = './input_g'
    inGreen: str = './input_i'
    output_dir: str = './output_rgb'
    maxthread: str = '10'
    creator_did: str = 'CDS/P/LSST/DP0'
    hips_creator: str = 'LIneA'
    obs_title: str = 'LSST DP0'
    luptonM: str = "0.02/0.02/0.02"
    luptonS: str = "0.005/0.005/0.007"
    luptonQ: str = "30/30/30"


