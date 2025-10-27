#!/bin/bash
#SBATCH -J HipsRGB
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=11
#SBATCH --propagate=NPROC

#mkdir -p $4
#touch $4/Moc.fits

java -Xmx20g -jar $2 -hipsgen -nocolor -maxthread=10 -param=$3 RGB

