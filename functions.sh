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

if [ -z $ALADIN_MAXMEM ];
then
  ALADIN_MAXMEM=$(expr `grep MemTotal /proc/meminfo | awk '{print $2}'` / 1024)
fi

if [ -z ALADIN_MAXTHREADS ];
then
  ALADIN_MAXTHREADS=$(cat /proc/cpuinfo | grep processor | wc -l)
fi

ALADIN_CMD="java -Xmx${ALADIN_MAXMEM}m -jar $ALADINPATH/AladinBeta.jar -hipsgen maxthread=$ALADIN_MAXTHREADS hips_creator='LIneA' obs_title='$HISP_TITLE' creator_did='$CREATOR_DID'"

function get_config_per_band() {
  case $1 in
    'g') echo $PIXELCUT_G ;;
    'r') echo $PIXELCUT_R ;;
    'i') echo $PIXELCUT_I ;;
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
  mkdir -p $BAND

  echo "Create initial hips per band"
  $ALADIN_CMD incremental=true in="'$IMGS'" out="'./$BAND'" pixelcut="'$PIXELCUT'" INDEX TILES JPEG
}

function create_hips_colour() {
  OUTPUT_DIR=$1

  cd $OUTPUT_DIR
  mkdir RGB
  touch RGB/Moc.fits    # note: apparently, ALADIN expects Moc.fits to exist before executing the RGB HiPS.

  PIXELCUT_G=$(get_config_per_band 'g')
  PIXELCUT_R=$(get_config_per_band 'r')
  PIXELCUT_I=$(get_config_per_band 'i')

  echo "Generation of one colour HiPS from 3 greyscale HiPS"
  $ALADIN_CMD inRed="'./i/'" inGreen="'./r/'" inBlue="'./g/'" cmRed="'${PIXELCUT_I}'" cmGreen="'${PIXELCUT_R}'" cmBlue="'${PIXELCUT_G}'" out='./RGB' RGB
}