#!/bin/bash
module load python/3.11/3.11.4
ROOTDIR=$HOME/PanOctober
ENVNAME=pan_october2025_env
source $ROOTDIR/venvs/$ENVNAME/bin/activate

cd $ROOTDIR
python check_reruns.py "$@"
