#!/bin/bash
#SBATCH -J createRGB
#SBATCH -p cpu_pipelines
#SBATCH -A hpc-pipelines
#SBATCH -N 1
#SBATCH -c 104
#SBATCH --exclusive
#SBATCH --propagate=NPROC

mkdir -p $4
touch $4/Moc.fits

java -Xmx$1g -jar $2 -hipsgen -nocolor -param=$3 RGB

