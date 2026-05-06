#!/bin/bash
CURRDIR=$(readlink -f $PWD)

module load python/3.11/3.11.4
ROOTDIR=/xdisk/ryant/chidiugonna/PAN/PAN_recreate_two/PanOctober
ENVNAME=pan_october2025_env
source $ROOTDIR/venvs/$ENVNAME/bin/activate

PYTHON=python

$PYTHON $CURRDIR/validate_pan.py "$@"
