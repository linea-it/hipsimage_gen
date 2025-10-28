#!/bin/bash
#SBATCH -J concatHIPS
#SBATCH -p cpu
#SBATCH -n 1
#SBATCH --cpus-per-task=11
#SBATCH --mem=22G
#SBATCH --propagate=NPROC
#SBATCH --time=10:00:00

# Concatenação hierárquica de HiPS
# $1 = max_mem (GB)
# $2 = aladin_jar
# $3 = config_file

srun --cpu-bind=cores java -Xmx20g -jar "$2" -hipsgen -nocolor -maxthread=10 -param="$3" CONCAT
