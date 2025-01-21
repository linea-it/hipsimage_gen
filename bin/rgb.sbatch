#!/bin/bash
#SBATCH -J createRGB
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH --propagate=NPROC

mkdir -p $4
touch $4/Moc.fits

java -Xmx$1g -jar $2 -hipsgen -nocolor -param=$3 RGB

