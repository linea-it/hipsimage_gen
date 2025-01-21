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

