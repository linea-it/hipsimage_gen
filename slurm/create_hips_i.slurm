#!/bin/bash
#SBATCH -p cpu_long
#SBATCH -J i-hipsimage
#SBATCH --exclusive

set -xe

echo 'BEGIN EXEC: '`date`

# directory where the Aladin executable is located.
export ALADINPATH=''
export OUTPUT_DIR=''
export INPUT_DIR=''

source functions.sh

# Create output dir
create_dir $OUTPUT_DIR

if [ $? -ne 0 ]; then
  echo "Create directories failed"
  exit 1
fi

# Execute HIPS i band
create_hips_per_band $INPUT_DIR i $OUTPUT_DIR

if [ $? -ne 0 ]; then
  echo "Create initial HIPS failed"
  exit 1
fi

echo 'FINISHED: '`date`
