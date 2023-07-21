#!/bin/bash

set -xe

export TILE='DES0354-1915'

export IMG_G='/mnt/EXT4/datasets/dr2/images/r4931/DES0354-1915/DES0354-1915_r4931p01_g.fits.fz'
export IMG_R='/mnt/EXT4/datasets/dr2/images/r4931/DES0354-1915/DES0354-1915_r4931p01_r.fits.fz'
export IMG_I='/mnt/EXT4/datasets/dr2/images/r4931/DES0354-1915/DES0354-1915_r4931p01_i.fits.fz'

export PIXELCUT_G='-1.23 508.7'
export PIXELCUT_R='-2.357 1039'
export PIXELCUT_I='-2.763 881.7'

source functions.sh

# Execute create dir
create_dir $TILE

if [ $? -ne 0 ]; then
  echo "Create directories failed"
  exit 1
fi

# Execute HIPS initial
create_hips_initial

if [ $? -ne 0 ]; then
  echo "Create initial HIPS failed"
  exit 1
fi

# Execute HIPS colour 
create_hips_colour

if [ $? -ne 0 ]; then
  echo "Create HIPS colour failed"
  exit 1
fi
