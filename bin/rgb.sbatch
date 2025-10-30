#!/bin/bash
#SBATCH -J HipsRGB
#SBATCH -p cpu
#SBATCH -n 1
#SBATCH --cpus-per-task=11
#SBATCH --mem=19G
#SBATCH --propagate=NPROC
#SBATCH --time=5:00:00

mkdir -p "$4"
touch "$4"/Moc.fits

srun --cpu-bind=cores java -Xmx18g -jar "$2" -hipsgen -nocolor -maxthread=10 -param="$3" RGB

