#!/bin/bash

module load python/3.8/3.8.2
CURRDIR=$PWD
cd /xdisk/nkchen/chidiugonna/condaenvs/
. ./startCondaPuma.sh
conda activate ./neuropython
cd $CURRDIR

PKG_DIR="/xdisk/nkchen/chidiugonna/PANpipelines/src"
LOCPY=${PKG_DIR}/panpipelines

export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$PWD/config/panpipeconfig_slurm.config

PIPELINES="freesurfer_panpipeline qsiprep_panpipeline tensor_panpipeline noddi_panpipeline fmriprep_panpipeline basil_voxelcalib aslprep_panpipeline textmeasures_freesurfer tensormeasures_xtract noddimeasures_xtract basilcalibmeasures_brainseg_newatlas  basilcalibmeasures_harvardcort basilcalibmeasures_harvardsubcort basilcalibmeasures_hcpmmp1aseg_newatlas collatecsv_panpipeline collatecsv_addbasil"

PARTICIPANTS="z6H55AAE"

python $DEBUG ${LOCPY}/pan_processing.py $CONFIG --pipelines $PIPELINES  --participant_label $PARTICIPANTS

