#!/bin/bash
module load python/3.11/3.11.4
source /xdisk/ryant/chidiugonna/PAN/PANDevelopment/venvs/pandev/bin/activate

PKG_DIR="/groups/ryant/PANapps/PANpipelines/src"
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH


jupyter lab
