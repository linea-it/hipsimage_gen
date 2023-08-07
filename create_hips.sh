#!/bin/bash

set -xe

echo 'BEGIN: '`date` 

export HISP_TITLE='DR2'
export CREATOR_DID='CDS/P/DES/DR2'
export OUTPUT_DIR='/home/singulani/projects/hipsimage_gen/tests/outputs'

function get_inputdir_per_band() {
  case $1 in
    'g') echo '/home/singulani/projects/hipsimage_gen/inputs/g' ;;
    'r') echo '/home/singulani/projects/hipsimage_gen/inputs/r' ;;
    'i') echo '/home/singulani/projects/hipsimage_gen/inputs/i' ;;
  esac
}

source functions.sh

# Create output dir
create_dir $OUTPUT_DIR

if [ $? -ne 0 ]; then
  echo "Create directories failed"
  exit 1
fi

# Execute HIPS initial to g,r,i bands
for i in 'g' 'r' 'i'
do
  DIR=$(get_inputdir_per_band $i)

  # echo "create_hips_per_band '$DIR' '$i' '$OUTPUT_DIR'"
  create_hips_per_band $DIR $i $OUTPUT_DIR

  if [ $? -ne 0 ]; then
    echo "Create initial HIPS failed"
    exit 1
  fi
done

# Create RGB
create_hips_colour $OUTPUT_DIR

if [ $? -ne 0 ]; then
  echo "Create HISP RGB failed"
  exit 1
fi

# Clear trash
clear_trash

echo 'FINISHED: '`date` 