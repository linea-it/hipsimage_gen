#!/bin/bash
#SBATCH -J HipsPNG
#SBATCH -p cpu
#SBATCH -n 1
#SBATCH --cpus-per-task=28
#SBATCH --mem=59G
#SBATCH --propagate=NPROC
#SBATCH --time=10:00:00

MAX_THREADS=${SLURM_CPUS_PER_TASK}
MAX_MEM="58G"

srun --cpu-bind=cores java -Xms${MAX_MEM} -Xmx${MAX_MEM} -jar "$2" -hipsgen -nocolor maxthread="${MAX_THREADS}" -param="$3" TILES PNG
