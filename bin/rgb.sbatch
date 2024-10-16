#!/bin/bash
#SBATCH -J hipsimage_g
#SBATCH -p cpu
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH --propagate=NPROC

mkdir ./RGB
touch ./RGB/Moc.fits

java -Xmx20g -jar /lustre/t0/scratch/users/singulani/slurm-home/aladin/Aladin.jar -hipsgen -nocolor maxthread=10 hips_creator=LIneA obs_title=Test01 creator_did=CDS/P/DES/DR2 inRed=./output_i inGreen=./output_r inBlue=./output_g luptonM="0.02/0.02/0.02" luptonS="0.005/0.005/0.007" luptonQ="30/30/30" out=./RGB RGB # 2>&1 >> RGB.log
