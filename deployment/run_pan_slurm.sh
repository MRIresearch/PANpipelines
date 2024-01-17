#!/bin/bash

# 1. Add commands here to start your python environment if required
# e.g. module load python//3.11/3.11.4and source /path/to/activate, or conda activate [ENVNAME]. 
module load python/3.11/3.11.4
source /xdisk/ryant/$USER/venvs/panvenv/bin/activate

# 2. Change PYTHON=python3 if this is required to access python version.
PYTHON=python

PKG_DIR="/xdisk/ryant/$USER/PANpipelines/src"
LOCPY=${PKG_DIR}/panpipelines

# 3. Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment. Just uncomment line below.
# export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$PWD/config/panpipeconfig_slurm.config

PARTICIPANTS="HML0182 vJ7xKAAS vleDFAA0 HML0253 HML0134 HML0223 xGwFuAAK HML0249 z6OYeAAM HML0173 11zUYBAA2 z7pAcAAI 7HY6AAM HML0153 HML0227 z5WEWAA2"

${PYTHON} ${LOCPY}/pan_processing.py $CONFIG  --participant_label $PARTICIPANTS

# Above construct, runs all the pipleines in the CONFIG
# Alternatively to run specific pipelines into an existing output directory define them in CONFIG if they don't already exist and then uncommnet
# the next three lines and comment out the run line above to use.
# PIPELINES="pipeline1 pipeline2"
# OUTPUT_DIR="/xdisk/ryant/chidiugonna/deployment/pan_output_20240106_214157_536401"
#${PYTHON} ${LOCPY}/pan_processing.py $CONFIG  --participant_label $PARTICIPANTS --pipelines $PIPELINES --pipeline_outdir $OUTPUT_DIR