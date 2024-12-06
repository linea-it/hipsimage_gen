#!/usr/bin/env python3
<<<<<<< HEAD
from dataclasses import replace, fields
from pathlib import Path
from shutil import which
from sys import argv
from typing import Union
import subprocess
from schemas import ColorConfig, RGBConfig
=======
from dataclasses import dataclass, replace, asdict
from os import environ, execv
from os.path import expandvars
from pathlib import Path

# from shlex import split
from shutil import which
from sys import argv
>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71
from yaml import safe_load
import configparser
import io


SBATCH_COLOR = 'color.sbatch'
SBATCH_RGB = 'rgb.sbatch'
COLORS = ["green", "red", "blue"]


<<<<<<< HEAD
=======
@dataclass
class IMGConfig:
    input_dir: str = "./input"
    output_dir: str = "./output"
    maxthread: str = "10"
    creator_did: str = "CDS/P/LSST/DP0"
    hips_creator: str = "LIneA"
    obs_title: str = "LSST DP0"
    incremental: str = "true"
    mode: str = "mean"
    pixelcut: str = "-1.2 400 asinh"
    cache: str = "./tmp"


>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71
def parse_cmdline():
    try:
        conffile = argv[1]
    except IndexError:
        conffile = "hips.yaml"

    return conffile


<<<<<<< HEAD
def load_configuration(config):
    _config = ColorConfig()
    return replace(_config, **config)
=======
def to_path(text):
    return Path(expandvars(text)).expanduser()
>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71


def find_prog(basename):
    prog = which(basename)

    if not prog:
        raise RuntimeError(f"program not found: {basename}")

    return prog

<<<<<<< HEAD

def sbatch(cmd, cwd):

    process = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    success_msg = 'Submitted batch job'
    stdout = process.stdout.decode('utf-8')

    if success_msg in stdout:
        job_id = int(stdout.split(' ')[3])
    else:
        stderr = process.stderr.decode('utf-8')
        print("Error: %s", stderr)
        exit(-1)
=======

def setup(config):
    config.sbatch = find_prog(config.sbatch)
    find_prog(config.rail_slurm_batch)
    find_prog(config.rail_slurm_py)

    if not config.inputdir.is_dir():
        raise RuntimeError("input directory not found: %s" % config.inputdir)

    if config.lepharedir:
        environ["LEPHAREDIR"] = config.lepharedir

    if config.lepharework:
        environ["LEPHAREWORK"] = config.lepharework

>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71

    return job_id

<<<<<<< HEAD
=======
    return "%d:%02d:%02d" % (hours, minutes, seconds)

>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71

def create_config_file(config, name, cwd):

    _config = Path(cwd, f"{name}.config")

<<<<<<< HEAD
    with open(_config, "w") as _conf:
        for field in fields(config):
            if field.name == 'input_dir':
                fieldname = 'in'
                value = Path(str(getattr(config, field.name))).absolute()
            elif field.name == 'output_dir':
                fieldname = 'out'
                value = Path(cwd, str(getattr(config, field.name)))
                value.mkdir(exist_ok=True)
                value = value.absolute()
            else:
                fieldname = field.name
                value = getattr(config, field.name)
 
            _conf.write(f'{fieldname}="{value}"\n')

    return _config
=======
    if config.time_limit is not None:
        cmd += ["--time=" + seconds_to_time(config.time_limit)]

    cmd += [
        config.rail_slurm_batch,
        config.inputdir,
        config.outputdir,
        "-a",
        config.algorithm,
    ]

    if config.param_file:
        cmd += ["-p", config.param_file]

    if config.calib_file:
        cmd += ["-c", config.calib_file]

    print(" ".join(str(x) for x in cmd))
    execv(config.sbatch, cmd)
    raise RuntimeError("error executing slurm")
>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71


def create_config_file(configs, output_file):
    """Create config file to hipsgen

    Args:
        output_file (str): config file
        configs (dict): hipsgen configuration
    """

    buf = io.StringIO()

    ini_writer = configparser.ConfigParser()

    for key, value in configs.items():
        if key == "input_dir":
            key = "in"
        elif key == "output_dir":
            key = "out"

        ini_writer.set("DEFAULT", str(key), str(value))

    ini_writer.write(buf)

    buf.seek(0)
    next(buf)
    with open(output_file, "w", encoding="UTF-8") as fd:
        fd.write(buf.read())

    return output_file


def load_configuration(configs):
    """_summary_

    Args:
        configs (_type_): _description_

    Returns:
        _type_: _description_
    """

    img_config = IMGConfig()
    return replace(img_config, **configs)


def main():
    """_summary_"""

    conffile = parse_cmdline()

    with open(conffile, encoding="UTF-8") as _file:
        config = safe_load(_file)

<<<<<<< HEAD
    aladin_cmd = config.get("aladin_cmd", "Aladin.jar")
    cwd = Path(config.get("cwd", "."))
    cwd.mkdir(exist_ok=True)
    max_mem = str(config.get("max_mem", "2"))

    hips_config = config.pop('hipsgen')
    hips_runs = hips_config.pop('runs')

    sbatch_color = find_prog(SBATCH_COLOR)
    sbatch_rgb = find_prog(SBATCH_RGB)

    colors_output = {}

    for color in COLORS:
        try:
            color_config = hips_runs[color]
            color_config.update(hips_config)
            config = load_configuration(color_config)
            color_config = create_config_file(config, color, cwd)
            colors_output[f'in{color.capitalize()}'] = Path(cwd, config.output_dir).absolute()
        except RuntimeError as e:
            print('Error: %s' % e)

        cmd = ["sbatch", sbatch_color, max_mem, aladin_cmd, color_config]
=======
    aladin = config.get("aladin_path", "Aladin.jar")
    cwd = config.get("cwd", ".")
    max_memory = config.get("max_memory", "2g")

    print(f"ALADIN: {aladin}")
    print(f"CWD: {cwd}")
    print(f"MAX MEMORY: {max_memory}")

    hipsgen_config = config.get("hipsgen", {})
    colors_config = config.get("colors", {})

    parallel_jobs = []

    for color in COLORS:
        img_config = hipsgen_config.copy()
        img_config.update(colors_config[color])

        try:
            img_config = asdict(load_configuration(img_config))
            print(f"COLOR {color}: {img_config}")
            create_config_file(img_config, Path(cwd, f"img.{color}"))
            # setup(config)
            # run(config)
        except RuntimeError as _err:
            print(f"Error: {_err}")
>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71

        try:
            job_id = sbatch(cmd, cwd)
            parallel_jobs.append(str(job_id))
        except RuntimeError as e:
            exit(-1)

<<<<<<< HEAD
    rgb_config = hips_runs['rgb']
    rgb_config.update(hips_config)
    rgb_config.update(colors_output)

    rgb_config_obj = replace(RGBConfig(), **rgb_config)

    rgb_config_file = create_config_file(rgb_config_obj, 'rgb', cwd)

    print("Submit Consolidate with dependencies: %s" % str(parallel_jobs))
    consolidate_job_id = sbatch(["sbatch", "--dependency=afterok:%s" % ",".join(parallel_jobs), sbatch_rgb, max_mem, aladin_cmd, rgb_config_file, str(rgb_config_obj.output_dir)], cwd)
    print("Consolidate job ID: %s" % consolidate_job_id)
=======
    # print("SUBMIT Consolidate with dependencies: %s" % str(parallel_jobs))
    # consolidate_job_id = sbatch(["sbatch", "--dependency=afterok:%s" % ",".join(parallel_jobs), config["rgb"]], cwd)
    # print("Consolidate JobID: %s" % consolidate_job_id)


if __name__ == "__main__":
    # config = {
    #     "rgb": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_color.sbatch",
    #     "green": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_r.sbatch",
    #     "red": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_i.sbatch",
    #     "blue": "/lustre/t0/scratch/users/singulani/hipsimage_gen/hipsimage_g.sbatch",
    # }
>>>>>>> 0df15f5b8b2758194cc4d3536adccd1873429a71


if __name__ == '__main__':
    main()

