#!/bin/bash
#SBATCH -J HipsINDEX
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=56
#SBATCH --propagate=NPROC


java -Xmx120g -jar $2 -hipsgen -nocolor -maxthread=55 -param=$3 INDEX

