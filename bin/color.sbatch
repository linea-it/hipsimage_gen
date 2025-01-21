#!/bin/bash
#SBATCH -J createHIPS
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH --propagate=NPROC

java -Xmx$1g -jar $2 -hipsgen -nocolor -param=$3 INDEX TILES PNG

