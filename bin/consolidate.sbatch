#!/bin/bash
#SBATCH -J consolidateHIPS
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH --propagate=NPROC

# Consolidação de regiões do HipsGen
# $1 = max_mem (GB)
# $2 = aladin_jar
# $3 = config_file

java -Xmx$1g -jar $2 -hipsgen -nocolor -param=$3 INDEX TILES PNG