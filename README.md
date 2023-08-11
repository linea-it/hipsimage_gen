# HiPSimage with Aladin

This guide outlines the steps required to install and run the HiPS (Hierarchical Progressive Surveys) image creation program using the Aladin software.

## Prerequisites

- [Aladin](https://aladin.u-strasbg.fr/aladin.gml) 

## Installation

1. Clone the program repository:
    ```sh
    git clone https://github.com/linea-it/hipsimage_gen
    cd hipsimage_gen
    ```

2. Copy `create_hips.sh.template` to `create_hips.sh`:
    ```sh
    cp create_hips.sh.template create_hips.sh
    ```

3. Modify the environment variables as needed in `create_hips.sh`:

    > WARNING: Note that ALADINPATH is mandatory.

    | Name | Mandatory | Default | Description |
    |------|----------|---------|-------------|
    | ALADINPATH | yes | - | Directory where the Aladin executable is located. |
    | HISP_TITLE | no | DR2 | HiPS title |
    | CREATOR_DID | no | CDS/P/DES/DR2 | HiPS identifier |
    | PIXELCUT_G | no | "-1.23 508.7 log" |  Allows you to specify how pixels are mapped in this value range to g band|
    | PIXELCUT_R | no | "-2.357 1039 log" |  Allows you to specify how pixels are mapped in this value range to r band|
    | PIXELCUT_I | no | "-2.763 881.7 log" |  Allows you to specify how pixels are mapped in this value range to i band|
    | HIPS_MAXMEM | no | all available in the system | Maximum memory used (in GB)|
    | HIPS_MAXTHREADS | no | all available in the system | Maximum threads used |
    | OUTPUT_DIR | no | './outputs' | Output dir |

4. Prepare source images:
    The source images must be separated by band in each directory: `g`, `r` and `i`.
    Example:
    ```sh
    tree inputs
    inputs
    ├── g
    │   ├── DES0354-1624_r4931p01_g.fits.fz
    │   ├── DES0354-1915_r4931p01_g.fits.fz
    │   ├── DES0354-1958_r4931p01_g.fits.fz
    │   └── DES2111-0207_r4575p01_g.fits.fz
    ├── i
    │   ├── DES0354-1624_r4931p01_i.fits.fz
    │   ├── DES0354-1915_r4931p01_i.fits.fz
    │   ├── DES0354-1958_r4931p01_i.fits.fz
    │   └── DES2111-0207_r4575p01_i.fits.fz
    └── r
        ├── DES0354-1624_r4931p01_r.fits.fz
        ├── DES0354-1915_r4931p01_r.fits.fz
        ├── DES0354-1958_r4931p01_r.fits.fz
        └── DES2111-0207_r4575p01_r.fits.fz
    ```

5. And each directory must be added in the function `get_inputdir_per_band` in its respective band (in `create_hips.sh`):
    ```sh
    function get_inputdir_per_band() {
    case $1 in
        'g') echo '<path/to/source/images/in/band/g>' ;;  # CHANGE PATH!
        'r') echo '<path/to/source/images/in/band/r>' ;;  # CHANGE PATH!
        'i') echo '<path/to/source/images/in/band/i>' ;;  # CHANGE PATH!
    esac
    }
    ```

## Execute
```sh
time ./create_hips.sh 2> error 1> log & 
```
