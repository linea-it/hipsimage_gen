#!/bin/bash

. env.sh

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

function get_config_per_band() {
  case $1 in
    'g') echo $PIXELCUT_G ;;
    'r') echo $PIXELCUT_R ;;
    'i') echo $PIXELCUT_I ;;
  esac
}

MEM=$(expr `grep MemTotal /proc/meminfo | awk '{print $2}'` / 1024)
THREADS=$(cat /proc/cpuinfo | grep processor | wc -l)
ALADIN_CMD="java -Xmx${MEM}m -jar $ALADINPATH/AladinBeta.jar -hipsgen maxthread=$THREADS hips_creator='LIneA' obs_title='$HISP_TITLE' creator_did='$CREATOR_DID'"

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
  mkdir -p $BAND

  echo "Create initial hips per band"
  $ALADIN_CMD incremental=true in="'$IMGS'" out="'./$BAND'" pixelcut="'$PIXELCUT'" INDEX TILES JPEG
}

function create_hips_colour() {
  OUTPUT_DIR=$1

  cd $OUTPUT_DIR
  mkdir RGB
  touch RGB/Moc.fits

  PIXELCUT_G=$(get_config_per_band 'g')
  PIXELCUT_R=$(get_config_per_band 'r')
  PIXELCUT_I=$(get_config_per_band 'i')

  echo "Generation of one colour HiPS from 3 greyscale HiPS"
  $ALADIN_CMD inRed="'./i/'" inGreen="'./r/'" inBlue="'./g/'" cmRed="'${PIXELCUT_I}'" cmGreen="'${PIXELCUT_R}'" cmBlue="'${PIXELCUT_G}'" out='./RGB' RGB
}

function clear_trash() {
  rm -rf $OUTPUT_DIR/g/
  rm -rf $OUTPUT_DIR/r/
  rm -rf $OUTPUT_DIR/i/
}
