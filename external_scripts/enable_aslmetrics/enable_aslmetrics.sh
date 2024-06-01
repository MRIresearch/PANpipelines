#!/bin/bash
module load matlab
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

sessions_file=<SESSIONS_FILE>
BIDS=<BIDS_DIR>
panout=<PIPELINE_DIR>
project="PAN_250_1"
basil_pipe="basil_voxel_mansdc"
basil_csf="basil_voxel_mansdc_single"
csvout=<WORKFLOW_DIR>/asl_metrics_matlab_20240601.csv

matlab -nodisplay -nodesktop -nosplash -r "enable_aslmetrics('${sessions_file}','${BIDS}','${panout}','${project}','${basil_pipe}','${basil_csf}','${csvout}');exit;"



