import neuroCombat
from panpipelines.utils.util_functions import drop_ses,updateParams,getParams,getGlob,getContainer,substitute_labels
import numpy as np
import pandas as pd
import glob
import os
import nibabel
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


def run_combat(pipeline_config_file):
  
    panpipeconfig_file=str(pipeline_config_file)
    labels_dict =None
    if os.path.exists(pipeline_config_file):
        IFLOGGER.info(f"{pipeline_config_file} exists.")
        with open(pipeline_config_file,'r') as infile:
            labels_dict = json.load(infile)
    
    try:
        basil_table = getGlob(getParams(labels_dict,"BASIL_TABLE"))
        basil_df = pd.read_csv(basil_table,sep=",")
        demo_table = getGlob(getParams(labels_dict,"DEMO_TABLE"))
        demo_df = pd.read_csv(demo_table,sep=",")
        omnibus_df = pd.merge(basil_df, demo_df,  how='left', left_on=["hml_id"], right_on =["hml_id"])

        mask=getParams(labels_dict,"BASIL_MASK")
        maskimg = nibabel.load(mask)
        maskdata = maskimg.get_fdata()
        (dimxx,dimyy,dimzz) = maskdata.shape

        #participants_label = getParams(labels_dict,'GROUP_PARTICIPANTS_LABEL')
        #participants_project = getParams(labels_dict,'GROUP_PARTICIPANTS_XNAT_PROJECT')
        #participants_session = getParams(labels_dict,'GROUP_SESSION_LABEL')
        #for part_vals in zip(participants_label,participants_project,participants_session):
        cbfrefimg = None
        basil_ref = getParams(labels_dict,"BASIL_DATAREF")
        data_masked=np.zeros((1,1))
        for dfnum in range(len(basil_df)):
            hmlid = basil_df.iloc[dfnum].hml_id
            project = basil_df.iloc[dfnum].site_id
            session = drop_ses(basil_df.iloc[dfnum].session_id)
            labels_dict = updateParams(labels_dict,"PARTICIPANT_LABEL",hmlid)
            labels_dict = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT",project)
            labels_dict = updateParams(labels_dict,"PARTICIPANT_SESSION",session)
            cbf=substitute_labels(basil_ref,labels_dict)
            if os.path.exists(cbf):
                cbfimg = nibabel.load(cbf)
                if dfnum == 0:
                    cbfrefimg = cbfimg 
                cbfdata = cbfimg.get_fdata()
                cbf_flat = cbfdata[maskdata > 0]
                cbf_flat_valid = np.zeros((len(cbf_flat),1))
                cbf_flat_valid[:,0]=cbf_flat
                if len(data_masked)>1:
                    data_masked = np.hstack((data_masked,cbf_flat_valid))
                else:
                    data_masked = cbf_flat_valid

        wf_dir = getParams(labels_dict,"WORKFLOW_DIR")
        output_dir = os.path.join(wf_dir,"combat_output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir,exist_ok=True)

        #if len(data_masked) > 1:
        #    np.savetxt(os.path.join(output_dir,'cbfdata.txt'), data_masked, fmt='%.18e', #delimiter=',')
  
        omnibus_df["batch"] = omnibus_df["site_id"].apply(lambda row: int(row.split("_")[0]))   
        batch_col =["batch"]

        health_medical_columns = [x for x in demo_df.columns if x.startswith("health_medical")]

        # To specify names of the variables that are categorical:
        #categorical_cols=["sex","handedness","race","hispanic_latino","highest_education_level_completed","memory_rank"] + health_medical_columns
        categorical_cols=["sex","handedness","race"]
        continuous_cols = ["age"]

        # Convert categorical columns to ordinal values, for specified columns
        covars_df = omnibus_df[["hml_id","subject_id","session_id","site_id"] + batch_col + categorical_cols + continuous_cols]

        # correct Nans
        covars_df.loc[:, categorical_cols] = covars_df.loc[:, categorical_cols].fillna("MISSING")
        covars_df.loc[:, continuous_cols] = covars_df.loc[:, continuous_cols].fillna(-1)

        covars_df = covars_df.apply(lambda col: pd.factorize(col)[0] + 1 if col.name in categorical_cols and col.dtype == 'object' else col)

        #Harmonization step:
        datamask_combat = neuroCombat.neuroCombat(dat=data_masked,
            covars=covars_df,
            batch_col=batch_col,
            continuous_cols=continuous_cols,
            categorical_cols=categorical_cols,
            ref_batch=3)
        harmonized = datamask_combat["data"]
        IFLOGGER.info("1st stage of harmonization completed")

        if not cbfrefimg:
            cbfrefimg = maskimg
        suffix = getParams(labels_dict,"COMBAT_SUFFIX")
        if not suffix:
            suffix="space-MNI152NLin6Asym_desc-combat_cbf"
        for dfnum in range(len(covars_df)):
            subject = covars_df.iloc[dfnum].subject_id
            project = covars_df.iloc[dfnum].site_id
            session = covars_df.iloc[dfnum].session_id
            print(f"processing {dfnum}: {subject} {session} {project}")
            cbf_template=np.zeros((dimxx,dimyy,dimzz))
            cbf_template[maskdata > 0]= harmonized[:,dfnum]
            cbf_combat_img = nibabel.Nifti1Image(cbf_template,cbfrefimg.affine,cbfrefimg.header)
            cbf_combat_file = os.path.join(output_dir,project,subject,session,f"{subject}_{session}_{suffix}.nii.gz")
            os.makedirs(os.path.dirname(cbf_combat_file),exist_ok=True)
            nibabel.save(cbf_combat_img,cbf_combat_file)

    except Exception as e:
        message = f"Exception caught: \n{e}"
        IFLOGGER.error(message)


def main():
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()
    pipeline_config_file = str(args.pipeline_config_file)

    run_combat(pipeline_config_file)

# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()

