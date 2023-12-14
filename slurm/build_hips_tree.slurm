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
build_tree $OUTPUT_DIR

if [ $? -ne 0 ]; then
  echo "(Re)build tree failed"
  exit 1
fi

echo 'FINISHED: '`date`
