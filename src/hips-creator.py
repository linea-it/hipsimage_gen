#!/usr/bin/env python3
from dataclasses import dataclass, replace, asdict
from os import environ, execv
from os.path import expandvars
from pathlib import Path

# from shlex import split
from shutil import which
from sys import argv
from yaml import safe_load
import configparser
import io


COLORS = ["green", "red", "blue"]


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


def parse_cmdline():
    try:
        conffile = argv[1]
    except IndexError:
        conffile = "hips.yaml"

    return conffile


def to_path(text):
    return Path(expandvars(text)).expanduser()


def find_prog(basename):
    prog = which(basename)

    if not prog:
        raise RuntimeError(f"program not found: {basename}")

    return prog


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


def seconds_to_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    return "%d:%02d:%02d" % (hours, minutes, seconds)


def run(config):
    cmd = [config.sbatch]

    if config.sbatch_args:
        cmd += config.sbatch_args

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

    #    print("SUBMIT %s..." % x)
    #    cmd = ["sbatch", config[x]]
    #    try:
    #        job_id = sbatch(cmd, cwd)
    #        parallel_jobs.append(str(job_id))
    #    except RuntimeError as e:
    #        exit(-1)

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

    main()
