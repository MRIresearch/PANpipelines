#!/bin/bash
module load matlab
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

sessions_file=/xdisk/ryant/chidiugonna/PAN250_Data/tsv/sessions.tsv
BIDS=/xdisk/ryant/chidiugonna/PAN250_Data/BIDS
panout=/xdisk/ryant/chidiugonna/PAN250_Deployment/pan250_processing_outputs
project="PAN_250_1"
basil_pipe="basil_voxel_mansdc"
basil_csf="basil_voxel_mansdc_single"
csvout=/xdisk/ryant/chidiugonna/PAN250_Deployment/pan250_processing_outputs/matlab_aslmetrics_script/group/matlab_aslmetrics_script_wf/asl_metrics_matlab_20240601.csv

matlab -nodisplay -nodesktop -nosplash -r "enable_aslmetrics('${sessions_file}','${BIDS}','${panout}','${project}','${basil_pipe}','${basil_csf}','${csvout}');exit;"



