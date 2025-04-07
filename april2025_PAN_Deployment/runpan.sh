#!/bin/bash

# 1. Add commands here to start your python environment if required
# e.g. module load python//3.11/3.11.4and source /path/to/activate, or conda activate [ENVNAME]. 
module load python/3.11/3.11.4

source /xdisk/trouard/chidiugonna/PAN/april2025_repro/venvs/pan_april2025_env/bin/activate
CURRDIR=$(readlink -f $PWD)

# 2. Change PYTHON=python3 if this is required to access python version.
PYTHON=python
PKG_DIR=/xdisk/trouard/chidiugonna/PAN/april2025_repro/venvs/pan_april2025_env/lib/python3.11/site-packages/

LOCPY=${PKG_DIR}/panpipelines

# 3. Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment. Just uncomment line below.
#export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$CURRDIR/config/pan.config.april2025
SESSIONSFILE="--sessions_file $CURRDIR/config/sessions.tsv"
PARTICIPANTS="HML0033 HML0227 HML0633 HML0130 HML0560 HML0191 HML0179 HML0490"
#PARTICIPANTS="ALL_SUBJECTS"

PROJECTS="001_HML 002_HML 003_HML 004_HML"

OUTDIR="$CURRDIR/april2025_processing_outputs"

#PIPELINES="--pipelines "
#DEPENDENT="--run_dependent_pipelines "

FORCERUN="--force_run True"
FORCERUN=""

DEBUG="-m pdb"
DEBUG=""

${PYTHON} ${DEBUG} ${LOCPY}/pan_processing.py $CONFIG $DEPENDENT $SESSIONSFILE $FORCERUN --participant_label $PARTICIPANTS  $PIPELINES --pipeline_outdir $OUTDIR --projects $PROJECTS
