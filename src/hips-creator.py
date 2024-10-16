#!/usr/bin/env python3
from dataclasses import dataclass, replace
from os import environ, execv
from os.path import expandvars
from pathlib import Path
from shlex import split
from shutil import which
from sys import argv, executable
from typing import Union

from yaml import safe_load


COLORS = ["green", "red", "blue"]


@dataclass
class IMGConfig:
    input_dir: str = './input_%s'
    output_dir: str = './output_%s'
    maxthread: str = '10'
    creator_did: str = 'CDS/P/LSST/DP0'
    hips_creator: str = 'LIneA'
    obs_title: str = 'LSST DP0'
    incremental: str = 'true'
    mode: str = 'mean'
    pixelcut: str = '-1.2 400 asinh'
    cache: str = './tmp_%s'
    cacheRemoveOnExit: str = 'false'


def parse_cmdline():
    try:
        conffile = argv[1]
    except IndexError:
        conffile = 'hips.yaml'

    return conffile

def to_path(text):
    return Path(expandvars(text)).expanduser()



def load_configuration(color, main_config):

    img_config = IMGConfig()

    config = main_config.copy() 

    hipsconf = config.get('hipsgen', {'runs': {color:{}}})
    print(hipsconf)
    runs = hipsconf.pop("runs")
    hipsconf.update(runs[color])

    img_config = replace(img_config, **hipsconf)

    config['hipsgen'] = img_config

    #config.in = config.in % color
    #config.out = config.out % color
    #config.cache = config.cache % color

    #config.in = to_path(config.in)
    #config.out = to_path(config.out)
    #config.cache = to_path(config.cache)

    #img_config = {
    #    "in": config.in,
    #    "out": config.out,
    #    "cache": config.cache,
    #    "maxthread": '10'
    #    "creator_did": str = 'CDS/P/LSST/DP
    #hips_creator: str = 'LIneA'
    #obs_title: str = 'LSST DP0'
    #incremental: str = 'true'
    #mode: str = 'mean'
    #pixelcut: str = '-1.2 400 asinh'
    #cache: str = './tmp_%s'
    #cacheRemoveOnExit: str = 'false'
    #}

    print(config)

    return config

def find_prog(basename):
    prog = which(basename)

    if not prog:
        raise RuntimeError('program not found: %s.' % basename)

    return prog

def setup(config):
    config.sbatch = find_prog(config.sbatch)
    find_prog(config.rail_slurm_batch)
    find_prog(config.rail_slurm_py)

    if not config.inputdir.is_dir():
        raise RuntimeError('input directory not found: %s' % config.inputdir)

    if config.lepharedir:
        environ['LEPHAREDIR'] = config.lepharedir

    if config.lepharework:
        environ['LEPHAREWORK'] = config.lepharework

def seconds_to_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return '%d:%02d:%02d' % (hours, minutes, seconds)

def run(config):
    cmd = [config.sbatch]

    if config.sbatch_args:
        cmd += config.sbatch_args

    if config.time_limit is not None:
        cmd += ['--time=' + seconds_to_time(config.time_limit)]

    cmd += [config.rail_slurm_batch, config.inputdir, config.outputdir, '-a',
            config.algorithm]

    if config.param_file:
        cmd += ['-p', config.param_file]

    if config.calib_file:
        cmd += ['-c', config.calib_file]

    print(' '.join(str(x) for x in cmd))
    execv(config.sbatch, cmd)
    raise RuntimeError('error executing slurm')


def main():

    parallel_jobs = []

    conffile = parse_cmdline()

    with open(conffile) as f:
        config = safe_load(f)

    cwd = config.get("cwd", ".")

    print("CWD: %s" % cwd)

    for color in COLORS:
        try:
            print("\nCOLOR: %s" % color)
            x = load_configuration(color, config)
            #setup(config)
            #run(config)
        except RuntimeError as e:
            print('Error: %s' % e)


    #    print("SUBMIT %s..." % x)
    #    cmd = ["sbatch", config[x]]
    #    try:
    #        job_id = sbatch(cmd, cwd)
    #        parallel_jobs.append(str(job_id))
    #    except RuntimeError as e:
    #        exit(-1)

    #print("SUBMIT Consolidate with dependencies: %s" % str(parallel_jobs))
    #consolidate_job_id = sbatch(["sbatch", "--dependency=afterok:%s" % ",".join(parallel_jobs), config["rgb"]], cwd)
    #print("Consolidate JobID: %s" % consolidate_job_id)

if __name__ == '__main__':
    config = {
        "rgb": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_color.sbatch",
        "green": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_r.sbatch", 
        "red": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_i.sbatch",
        "blue": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_g.sbatch"
    }

    main()
