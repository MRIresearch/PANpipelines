#!/bin/bash

# Here you will need to load your python environment
# module load python/3.8/3.8.2

PKG_DIR="/xdisk/nkchen/chidiugonna/PANpipelines/src"
LOCPY=${PKG_DIR}/panpipelines

export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$PWD/config/panpipeconfig_slurm.config

PIPELINES="freesurfer_panpipeline qsiprep_panpipeline tensor_panpipeline noddi_panpipeline fmriprep_panpipeline basil_voxelcalib aslprep_panpipeline textmeasures_freesurfer tensormeasures_xtract noddimeasures_xtract basilcalibmeasures_brainseg_newatlas  basilcalibmeasures_harvardcort basilcalibmeasures_harvardsubcort basilcalibmeasures_hcpmmp1aseg_newatlas collatecsv_panpipeline collatecsv_addbasil"
PIPELINES="freesurfer_panpipeline"
PARTICIPANTS="z6H55AAE"

# assume python is called as python but might be python3
python $DEBUG ${LOCPY}/pan_processing.py $CONFIG --pipelines $PIPELINES  --participant_label $PARTICIPANTS

