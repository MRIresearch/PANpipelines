#!/bin/bash

module load python/3.8/3.8.2
CURRDIR=$PWD
cd /xdisk/nkchen/chidiugonna/condaenvs/
. ./startCondaPuma.sh
conda activate ./neurodev
cd $CURRDIR

CONFIG=$PWD/config/panpipeconfig.json
PIPELINES="qsiprep_0-18-1_panpipeline tensor_0-18-1_panpipeline noddi_0-18-1_panpipeline fmriprep_23-1-3_panpipeline fmriprep_panpipeline qsiprep_panpipeline tensor_panpipeline noddi_panpipeline"
PIPELINES="fmriprep_23-1-3"
DEBUG="-m pdb"
DEBUG=""
PARTICIPANTS="z6H55AAE z6kmyAAE vKSqqAAG vLWVIAA4 vLorJAAS xGfrQAAS vJ8brAAC skrxHAAQ"
PARTICIPANTS="z6H55AAE"

python $DEBUG pan_processing.py $CONFIG --pipelines $PIPELINES  --participant_label $PARTICIPANTS

