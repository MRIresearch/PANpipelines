#!/bin/bash

# 1. Add commands here to start your python environment if required
# e.g. module load python//3.11/3.11.4and source /path/to/activate, or conda activate [ENVNAME]. 
module load python/3.11/3.11.4
source /xdisk/ryant/$USER/PAN250_Deployment/venvs/pan250_env/bin/activate

# 2. Change PYTHON=python3 if this is required to access python version.
PYTHON=python

PKG_DIR=/xdisk/ryant/$USER/PAN250_Deployment/venvs/pan250_env/lib/python3.11/site-packages/
PKG_DIR="/xdisk/ryant/$USER/PANpipelines/src"
LOCPY=${PKG_DIR}/panpipelines

# 3. Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment. Just uncomment line below.
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

#CONFIG=$PWD/config/MILESTONE.20240517.pan250.config
CONFIG=$PWD/config/pan250.config

PARTICIPANTS='ALL_SUBJECTS'

PROJECTS="PAN_250_1"

OUTDIR="$PWD/20240530_pan250_processing_outputs"
PIPELINES="--pipelines freesurf basil_voxel_mansdc preproc_panpipeline"


${PYTHON} ${DEBUG} ${LOCPY}/pan_processing.py $CONFIG  $SESSIONS --participant_label $PARTICIPANTS  $PIPELINES --pipeline_outdir $OUTDIR --projects $PROJECTS


