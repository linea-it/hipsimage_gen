#!/usr/bin/env python3
from dataclasses import replace, fields
from pathlib import Path
from shutil import which
from sys import argv
from typing import Union
import subprocess
from schemas import ColorConfig, RGBConfig
from yaml import safe_load


SBATCH_COLOR = 'color.sbatch'
SBATCH_RGB = 'rgb.sbatch'
COLORS = ["green", "red", "blue"]


def parse_cmdline():
    try:
        conffile = argv[1]
    except IndexError:
        conffile = 'hips.yaml'

    return conffile


def load_configuration(config):
    _config = ColorConfig()
    return replace(_config, **config)


def find_prog(basename):
    prog = which(basename)

    if not prog:
        raise RuntimeError('program not found: %s.' % basename)

    return prog


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

    return job_id


def create_config_file(config, name, cwd):

    _config = Path(cwd, f"{name}.config")

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


def main():

    parallel_jobs = []

    conffile = parse_cmdline()

    with open(conffile) as f:
        config = safe_load(f)

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

        try:
            job_id = sbatch(cmd, cwd)
            parallel_jobs.append(str(job_id))
        except RuntimeError as e:
            exit(-1)

    rgb_config = hips_runs['rgb']
    rgb_config.update(hips_config)
    rgb_config.update(colors_output)

    rgb_config_obj = replace(RGBConfig(), **rgb_config)

    rgb_config_file = create_config_file(rgb_config_obj, 'rgb', cwd)

    print("Submit Consolidate with dependencies: %s" % str(parallel_jobs))
    consolidate_job_id = sbatch(["sbatch", "--dependency=afterok:%s" % ",".join(parallel_jobs), sbatch_rgb, max_mem, aladin_cmd, rgb_config_file, str(rgb_config_obj.output_dir)], cwd)
    print("Consolidate job ID: %s" % consolidate_job_id)


if __name__ == '__main__':
    main()

