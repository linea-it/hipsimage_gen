#!/bin/bash

set -xe

PIXELCUT='-1.23 508.7'

IMGS='/home/singulani/projects/hipsimage/inputs/g'
BAND='g'

source functions.sh

# Execute create dir
create_dir $BAND

if [ $? -ne 0 ]; then
  echo "Create directories failed"
  exit 1
fi

# Execute HIPS initial
create_hips_initial $IMGS $PIXELCUT

if [ $? -ne 0 ]; then
  echo "Create initial HIPS failed"
  exit 1
fi
