#!/bin/bash
CONFIG=$PWD/config/panpipeconfig_example.config

PIPELINES="basil_voxelcalib"

PARTICIPANTS="z6H55AAE"

python $DEBUG pan_processing.py $CONFIG --pipelines $PIPELINES  --participant_label $PARTICIPANTS

