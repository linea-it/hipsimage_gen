#!/bin/bash
#SBATCH -J hipsRegion
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=5
#SBATCH --propagate=NPROC

java -Xmx$1g -jar $2 -hipsgen -nocolor -param=$3 INDEX TILES PNG

