#!/bin/bash
export SINGULARITY_CACHEDIR=/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/singularitycache 
SINGNAME=panprocminimal-v0.2.sif
DOCKERURI=docker://aacazxnat/panproc-minimal:0.2
singularity build $SINGNAME $DOCKERURI

SINGNAME=qsiprep-0.21.4.sif
DOCKERURI=docker://pennbbl/qsiprep:0.21.4
singularity build $SINGNAME $DOCKERURI

SINGNAME=fmriprep-24.1.1.sif
DOCKERURI=docker://nipreps/fmriprep:24.1.1 
singularity build $SINGNAME $DOCKERURI

SINGNAME=tractseg.sif 
DOCKERURI=docker://wasserth/tractseg_container:master
singularity build $SINGNAME $DOCKERURI

SINGNAME=xcpd-0.10.5.sif
DOCKERURI=docker://pennlinc/xcp_d:0.10.5 
singularity build $SINGNAME $DOCKERURI

SINGNAME=panapps.sif
DOCKERURI=docker://aacazxnat/panproc-apps:0.1 
singularity build $SINGNAME $DOCKERURI