from panpipelines.utils.util_functions import getParams,getGlob,getContainer,substitute_labels
from panpipelines.utils.transformer import ants_registration_rigid
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from functools import partial
import os
from nipype import logging as nlogging
import json

IFLOGGER=nlogging.getLogger('nipype.interface')

def _path_exists(path, parser):
    """Ensure a given path exists."""
    if path is None or not Path(path).exists():
        raise parser.error(f"Path does not exist: <{path}>.")
    return Path(path).expanduser().absolute()

def parse_params():
    parser = ArgumentParser(description="additional_transforms")
    PathExists = partial(_path_exists, parser=parser)
    parser.add_argument("pipeline_config_file", type=PathExists, help="Pipeline Config File")
    return parser


def create_transforms(pipeline_config_file):
  
    panpipeconfig_file=str(pipeline_config_file)
    labels_dict =None
    if os.path.exists(pipeline_config_file):
        IFLOGGER.info(f"{pipeline_config_file} exists.")
        with open(pipeline_config_file,'r') as infile:
            labels_dict = json.load(infile)
    
    try:
        
        t1w=getGlob(substitute_labels("<BIDS_DIR>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/anat/*_T1w.nii.gz",labels_dict))
        # if we cant' find T1w then this must be a situation where we have to use the second session MPRAGE
        if not t1w:
            t1w=getGlob(substitute_labels("<BIDS_DIR>/sub-<PARTICIPANT_LABEL>/*/anat/*_T1w.nii*",labels_dict))
        # use wildcard in QSIANAT
        qsianat=getGlob(getParams(labels_dict,"QSIANAT"))
        t1w_t1acpc=getParams(labels_dict,"T1W_T1ACPC")
        command_base, container = getContainer(labels_dict,nodename="additional_transforms",SPECIFIC="DUMMY_CONTAINER",LOGGER=IFLOGGER)
        transform_complete=ants_registration_rigid(t1w,qsianat,t1w_t1acpc,command_base)


    except Exception as e:
        message = f"Exception caught: \n{e}"
        IFLOGGER.error(message)


def main():
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()
    pipeline_config_file = str(args.pipeline_config_file)

    create_transforms(pipeline_config_file)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
