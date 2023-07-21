#!/bin/bash

. env.sh

ALADIN_CMD="java -Xmx20000m -jar $ALADINPATH/AladinBeta.jar -hipsgen "

function create_dir() {
  BAND=$1

  mkdir -p outputs/$BAND
  cd outputs/$BAND
}

function create_hips_initial() {
  IMGS=$1
  PIXELCUT="'$2 log'"
  echo "Create initial hips per band"
  $ALADIN_CMD maxthread=10 incremental=true in="'$IMGS'" out="'.'" hips_creator='LIneA' obs_title='DES_DR2' pixelcut=$PIXELCUT creator_did='AUTH/P/LIN' INDEX TILES JPEG MOC
}

function create_hips_colour() {
  echo "Generation of one colour HiPS from 3 greyscale HiPS"
  $ALADIN_CMD maxthread=10 inRed='./hips_i/AUTH_P_LIN' inGreen='./hips_r/AUTH_P_LIN' inBlue='./hips_g/AUTH_P_LIN' cmRed="'${PIXELCUT_I} log'" cmGreen="'${PIXELCUT_R} log'" cmBlue="'${PIXELCUT_G} log'" creator_did='AUTH/P/LIN' out='./hips_RGB' RGB
}
