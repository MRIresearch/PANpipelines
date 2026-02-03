#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

SINGIMAGE=$1
ANATDIR=$2
SUB=$3
SES=$4
OUTDIR=$5
NTH=$6
DEVICE=$7
CLIPPING=$8

echo "singularity run --nv $SINGIMAGE --device $DEVICE --t1 $ANATDIR/${SUB}_${SES}_rec-defaced_T1w.nii.gz --flair $ANATDIR/${SUB}_${SES}_rec-defaced_FLAIR.nii.gz  --output ${OUTDIR}/results --temp ${OUTDIR}/temp --probability_map --clipping $CLIPPING --threads $NTH"

singularity run --nv $SINGIMAGE --device $DEVICE --t1 $ANATDIR/${SUB}_${SES}_rec-defaced_T1w.nii.gz --flair $ANATDIR/${SUB}_${SES}_rec-defaced_FLAIR.nii.gz  --output ${OUTDIR}/results --temp ${OUTDIR}/temp --probability_map --clipping $CLIPPING --threads $NTH


