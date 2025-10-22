# HiPSimage with Aladin

This guide outlines the steps required to install and run the HiPS (Hierarchical Progressive Surveys) image creation program using the Aladin software.

## Prerequisites

- [Aladin](https://aladin.u-strasbg.fr/aladin.gml)

## Installation

```sh
git clone https://github.com/linea-it/hipsimage_gen
cd hipsimage_gen
conda env create -f environment.yml
conda activate hipsimage
export PATH=`pwd`/bin:$PATH
cp param.example.yaml param.yaml
```

**Modify param.yml with information regarding your imagens generation.**


## Execute
```sh
hips-creator param.yaml
```

## HIPS execution on LIneA
https://docs.google.com/document/d/1yn-Uuax0VCVMxA4PsGHCwaoY43Dz-BIj6wrUUEXLGUQ/


## Tests

# Particionamento por banda:

- Bandas
```
java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color
    in=/mnt/EXT4/datasets/dr2_images/[g,r,i]
    out=/mnt/EXT4/hips/dc2/main/[g,r,i] INDEX TILES PNG
```

- RGB
```
java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color
    inRed=/mnt/EXT4/hips/dc2/main/i
    inGreen=/mnt/EXT4/hips/dc2/main/r
    inBlue=/mnt/EXT4/hips/dc2/main/g

    luptonM="0.03/0.03/0.03"
    luptonS="0.4/0.4/0.4"
    luptonQ="40000/40000/40000"

    out=/mnt/EXT4/hips/dc2/main/rgb RGB
```

# Particionamento por region

- bandas por region
```
java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color
    in=/mnt/EXT4/datasets/dr2_images/[g,r,i]
    out=/mnt/EXT4/hips/dc2/test01/[region]/[g,r,i]
    region=[region] INDEX TILES PNG
```

- RGB por region
```
java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color
    inRed=/mnt/EXT4/hips/dc2/test01/N11.47518557_47519863/i
    inGreen=/mnt/EXT4/hips/dc2/test01/N11.47518557_47519863/r
    inBlue=/mnt/EXT4/hips/dc2/test01/N11.47518557_47519863/g

    luptonM="0.03/0.03/0.03"
    luptonS="0.4/0.4/0.4"
    luptonQ="40000/40000/40000"

    out=/mnt/EXT4/hips/dc2/test01/N11.47518557_47519863/rgb RGB
```



