#!/bin/bash

# Add commands here to start your python environment if required
# e.g. module load python/3.8/3.8.2 or conda activate [ENVNAME]

# module load python/3.8/3.8.2

# Change PYTHON=python3 if this is required to access python version.
PYTHON=python

PKG_DIR="/xdisk/nkchen/chidiugonna/PANpipelines/src"
LOCPY=${PKG_DIR}/panpipelines

# Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment
#export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$PWD/config/panpipeconfig_slurm.config

PARTICIPANTS="15FDNYAA4 z7N36AAE"

${PYTHON} ${LOCPY}/pan_processing.py $CONFIG  --participant_label $PARTICIPANTS

