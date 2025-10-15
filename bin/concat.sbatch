#!/bin/bash
#SBATCH -J concatHIPS
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=5
#SBATCH --propagate=NPROC

# Concatenação hierárquica de HiPS
# $1 = max_mem (GB)
# $2 = aladin_jar
# $3 = config_file

java -Xmx$1g -jar $2 -hipsgen -nocolor -param=$3 CONCAT
