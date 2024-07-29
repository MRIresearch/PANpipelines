#!/bin/bash

# 1. Add commands here to start your python environment if required
# e.g. module load python//3.11/3.11.4and source /path/to/activate, or conda activate [ENVNAME]. 
. /media/mercury/chidiugonna/condaenvs/startconda.sh
conda activate /media/mercury/chidiugonna/condaenvs/neurodev

# 2. Change PYTHON=python3 if this is required to access python version.
PYTHON=python

PKG_DIR="/media/mercury/chidiugonna/Repos/PANpipelines/src"
#PKG_DIR="/media/mercury/chidiugonna/condaenvs/neurodev/lib/python3.11/site-packages"
LOCPY=${PKG_DIR}/panpipelines

# 3. Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment. Just uncomment line below.
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$PWD/config/pan250.config.dockerbind

#PARTICIPANTS="HML0001 HML0002 HML0003 HML0004 HML0046 HML0080 HML0249 HML0273"

PARTICIPANTS='ALL_SUBJECTS'
PARTICIPANTS="HML0076 HML0080"

PROJECTS="PAN_250_1"

OUTDIR="$PWD/pan250_dockerbind_processing_outputs_2subj"
PIPELINES="--pipelines preproc_panpipeline basilmeasures_arterial_native_pvcorr_gm basilmeasures_arterial_native_pvcorr_gm_maskchem basilmeasures_arterial_native_pvcorr_wm_maskchem collategroup_arterial collate_subject_arterial"
#DEBUG="-m pdb"

${PYTHON} ${DEBUG} ${LOCPY}/pan_processing.py $CONFIG  --participant_label $PARTICIPANTS $PIPELINES --pipeline_outdir $OUTDIR --projects $PROJECTS


