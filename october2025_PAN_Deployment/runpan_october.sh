#!/bin/bash

# 1. Add commands here to start your python environment if required
# e.g. module load python//3.11/3.11.4and source /path/to/activate, or conda activate [ENVNAME]. 
module load python/3.11/3.11.4

source /xdisk/ryant/chidiugonna/PAN/PAN_recreate/venvs/pan_october2025_env/bin/activate
CURRDIR=$(readlink -f $PWD)

# 2. Change PYTHON=python3 if this is required to access python version.
PYTHON=python
PKG_DIR=/xdisk/ryant/chidiugonna/PAN/PAN_recreate/venvs/pan_october2025_env/lib/python3.11/site-packages/

LOCPY=${PKG_DIR}/panpipelines

# 3. Export python path in case 'panpipelines' python package not accessible. This should not be necessary if
# panpipelines has been installed in yout python environment. Just uncomment line below.
#export PYTHONPATH=${PKG_DIR}:$PYTHONPATH

CONFIG=$CURRDIR/config/pan.config.oct2025
#SESSIONSFILE="--sessions_file $CURRDIR/config/sessions.tsv"
PARTICIPANTS="--participant_label HML0112 HML0315 HML0605 HML0511 HML0368 HML0853 HML0460 HML0778"

#PARTICIPANTS="ALL_SUBJECTS"
#QUERY="--participant_query (df.hml_id.isin([<PARTICIPANTS>])) & (df.index > 0) & (df.index < 41)"

PROJECTS="PAN_October_2025"

OUTDIR="$CURRDIR/october2025_processing_outputs"

PIPELINES="--pipelines mriqc"
#DEPENDENT="--run_dependent_pipelines "

FORCERUN="--force_run True"
FORCERUN=""

DEBUG="-m pdb"
DEBUG=""

NOCHECK=""
NOCHECK="--run_interactive False"

${PYTHON} ${DEBUG} ${LOCPY}/pan_processing.py $CONFIG $DEPENDENT $SESSIONSFILE $FORCERUN $PARTICIPANTS $QUERY $PIPELINES --pipeline_outdir $OUTDIR --projects $PROJECTS $NOCHECK
