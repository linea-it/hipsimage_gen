#!/bin/bash
#SBATCH -p cpu_long
#SBATCH -J rgb-hipsimage
#SBATCH --exclusive

set -xe

echo 'BEGIN EXEC: '`date`

# directory where the Aladin executable is located.
export ALADINPATH=''
export OUTPUT_DIR=''

source functions.sh

# Create RGB
create_hips_colour $OUTPUT_DIR

if [ $? -ne 0 ]; then
  echo "Create HISP RGB failed"
  exit 1
fi

echo 'FINISHED: '`date`
