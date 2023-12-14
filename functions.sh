#!/bin/bash

if [ -z $HISP_TITLE ];
then
  HISP_TITLE='DR2'
fi

if [ -z $CREATOR_DID ];
then
  CREATOR_DID='CDS/P/DES/DR2'
fi

if [ -z $PIXELCUT_G ];
then
  PIXELCUT_G='-1.23 508.7 log'
fi

if [ -z $PIXELCUT_R ];
then
  PIXELCUT_R='-2.357 1039 log'
fi

if [ -z $PIXELCUT_I ];
then
  PIXELCUT_I='-2.763 881.7 log'
fi

if [ -z $HIPS_MAXMEM ];
then
  HIPS_MAXMEM=$(expr `grep MemTotal /proc/meminfo | awk '{print $2}'` / 1024 / 1024)
fi

if [ -z HIPS_MAXTHREADS ];
then
  HIPS_MAXTHREADS=$(cat /proc/cpuinfo | grep processor | wc -l)
fi

ALADIN_CMD="java -Xmx${HIPS_MAXMEM}g -jar $ALADINPATH/AladinBeta.jar -hipsgen -nocolor maxthread=$HIPS_MAXTHREADS"
ALADIN_CMD="$ALADIN_CMD hips_creator=LIneA obs_title=$HISP_TITLE creator_did=$CREATOR_DID"

function get_config_per_band() {
  case $1 in
    'g') echo ${PIXELCUT_G} ;;
    'r') echo ${PIXELCUT_R} ;;
    'i') echo ${PIXELCUT_I} ;;
  esac
}

function create_dir() {
  OUTPUT_DIR=$1
  mkdir -p $OUTPUT_DIR
}

function create_hips_per_band() {
  IMGS=$1
  BAND=$2
  PIXELCUT=$(get_config_per_band $BAND)
  OUTPUT_DIR=$3

  cd $OUTPUT_DIR
  mkdir -p $BAND tmp_$BAND

  echo "Create initial hips per band: "$BAND
  $ALADIN_CMD incremental=true in=$IMGS out=./$BAND mode=keeptile cache=./tmp_$BAND cacheRemoveOnExit=false pixelcut="'${PIXELCUT}'" INDEX TILES JPEG 2>&1 >> $OUTPUT_DIR/hips_$BAND.log

}

function create_hips_colour() {
  OUTPUT_DIR=$1
  cd $OUTPUT_DIR
  mkdir -p RGB
  touch RGB/Moc.fits    # note: apparently, ALADIN expects Moc.fits to exist before executing the RGB HiPS.

  echo "Generation of one colour HiPS from 3 greyscale HiPS"
  $ALADIN_CMD inRed=./i/ inGreen=./r/ inBlue=./g/ luptonM="0.02/0.02/0.02" luptonS="0.005/0.005/0.007" luptonQ="30/30/30" out=./RGB RGB 2>&1 >> $OUTPUT_DIR/hips_RGB.log
}

function build_tree() {
  OUTPUT_DIR=$1
  FRAME=${2:-equatorial}

  echo "(Re)build HiPS tree. (Frame: $FRAME)"
  echo "--> outputdir: "$OUTPUT_DIR
  $ALADIN_CMD out=$OUTPUT_DIR frame=$FRAME TREE 2>&1 >> ./hips_tree.log
}
