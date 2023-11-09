#!/bin/bash

# Add commands here to start your python environment if required
# e.g. module load python/3.8/3.8.2

PKG_DIR="/xdisk/nkchen/chidiugonna/PANpipelines/src"
LOCPY=${PKG_DIR}/panpipelines

# Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$PWD/config/panpipeconfig_slurm.config

PIPELINES="freesurfer_panpipeline qsiprep_panpipeline tensor_panpipeline noddi_panpipeline fmriprep_panpipeline basil_voxelcalib aslprep_panpipeline textmeasures_freesurfer tensormeasures_xtract noddimeasures_xtract basilcalibmeasures_brainseg_newatlas  basilcalibmeasures_harvardcort basilcalibmeasures_harvardsubcort basilcalibmeasures_hcpmmp1aseg_newatlas collatecsv_panpipeline collatecsv_addbasil"
PIPELINES="freesurfer_panpipeline"
PARTICIPANTS="z6H55AAE z6kmyAAE"

# assume python is called as python but might be python3
python ${LOCPY}/pan_processing.py $CONFIG --pipelines $PIPELINES  --participant_label $PARTICIPANTS

