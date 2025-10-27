#!/bin/bash
#SBATCH -J HipsPNG
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=11
#SBATCH --propagate=NPROC

java -Xmx20g -jar $2 -hipsgen -nocolor -maxthread=10 -param=$3 TILES PNG
