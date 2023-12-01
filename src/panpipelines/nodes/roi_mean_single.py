from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
import pandas as pd
import json
import datetime
from pathlib import Path
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def roi_mean_single_proc(labels_dict,input_file,atlas_file,atlas_index):

    cwd=os.getcwd()
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')

    if not session_label:
        roi_output_dir = os.path.join(cwd,f"sub-{participant_label}_roi_output_dir")
    else:
        roi_output_dir = os.path.join(cwd,f"sub-{participant_label}_ses-{session_label}_roi_output_dir")

    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    if Path(atlas_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir)

        NEUROIMG=getParams(labels_dict,"NEURO_CONTAINER")
        atlas_file_nii = newfile(mgzdir,atlas_file,extension=".nii.gz")
        convMGZ2NII(atlas_file, atlas_file_nii, NEUROIMG)
        atlas_file = atlas_file_nii

    if Path(input_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir)

        NEUROIMG=getParams(labels_dict,"NEURO_CONTAINER")
        input_file_nii = newfile(mgzdir,input_file,extension=".nii.gz")
        convMGZ2NII(input_file, input_file_nii, NEUROIMG)
        input_file = input_file_nii

    if not session_label:
        roi_raw_txt = os.path.join(roi_output_dir,f"{participant_label}_roi_raw.txt")
    else:
        roi_raw_txt = os.path.join(roi_output_dir,f"{participant_label}_{session_label}_roi_raw.txt")


    atlas_type="3D"

    atlas_img  = nib.load(atlas_file)
    image_shape = atlas_img.header.get_data_shape()
    if len(image_shape) > 3:
        atlas_type="4D"

    if atlas_type == "4D":
        params = " -i "+input_file+ \
            " -d "+atlas_file + \
            " -o "+roi_raw_txt

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fsl_glm"\
                " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)
    else:
        params = " -i "+input_file+ \
            " -o "+roi_raw_txt+\
            " --label="+atlas_file
            
        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmeants"\
                " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)     

    if atlas_index.split(":")[0] == "get_freesurfer_atlas_index":
        lutfile = substitute_labels(atlas_index.split(":")[1],labels_dict)
        new_atlas_index=newfile(roi_output_dir,atlas_file,suffix="desc-index",extension=".txt")
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,new_atlas_index)
        atlas_index=new_atlas_index

    with open(atlas_index, 'r') as in_file:
        lines = in_file.readlines()

    table_columns = [x.replace('\n','') for x in lines]
    df2 = pd.read_table(roi_raw_txt,sep=r"\s+",header=None)
    numrows = len(df2)
    
    csv_basename = ""

    atlas_name = getParams(labels_dict,'ATLAS_NAME')
    if not atlas_name:
        atlas_name = os.path.basename(atlas_file).split('.')[0].split('_')[0].split('-')[0]
    csv_basename = f"atlas-{atlas_name}"

    modality = get_bidstag("desc",input_file,True)
    if modality:
        modality=modality[-1].split(".")[0]
        csv_basename = csv_basename + "_" + modality
    else:
        modality = os.path.basename(input_file).split('.')[0].split('_')[-1].split('-')[-1]
        csv_basename = csv_basename + "_" + modality

    table_columns = [f"{atlas_name}.{x}.{modality}" for x in table_columns]

    if not session_label:
        csv_basename  = f"sub-{participant_label}" + "_" + csv_basename
    else:
        csv_basename  = f"sub-{participant_label}_ses-{session_label}" + "_" + csv_basename

    roi_csv = os.path.join(roi_output_dir,'{}.csv'.format(csv_basename))

    if numrows < 2:
        if session_label:
            df2.insert(0,"session_id",["ses-"+session_label])
            table_columns.insert(0,"session_id")
        else:
            df2.insert(0,"session_id",["NotProvided"])
            table_columns.insert(0,"session_id")

        df2.insert(0,"subject_id",["sub-"+participant_label])
        table_columns.insert(0,"subject_id")

        df2.columns = table_columns
        df2.to_csv(roi_csv,sep=",",header=True, index=False)
    else:
        flat_vals=[]
        flat_tablecolumns=[]
        for count in range(numrows):
            flat_vals.extend(df2.iloc[count].to_list())
            flat_tablecolumns.extend([x + f".{count}" for x in table_columns])
        newdf=pd.DataFrame([flat_vals])
        if session_label:
            newdf.insert(0,"session_id",["ses-"+session_label])
            flat_tablecolumns.insert(0,"session_id")
        else:
            newdf.insert(0,"session_id",["NotProvided"])
            flat_tablecolumns.insert(0,"session_id")
        newdf.insert(0,"subject_id",["sub-"+participant_label])
        flat_tablecolumns.insert(0,"subject_id")
        newdf.columns = flat_tablecolumns
        newdf.to_csv(roi_csv,sep=",",header=True, index=False)


    metadata = {}
    roi_json = os.path.join(roi_output_dir,'{}.json'.format(csv_basename))
    metadata = updateParams(metadata,"Title","roi_mean_single")
    metadata = updateParams(metadata,"Description","Extract Measures from Image file using provided atlas.")
    metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
    metadata = updateParams(metadata,"Atlas File",atlas_file)
    metadata = updateParams(metadata,"Atlas Labels",atlas_index)
    metadata = updateParams(metadata,"Input File",atlas_index)
    metadata = updateParams(metadata,"Command",evaluated_command)
    export_labels(metadata,roi_json)


    out_files=[]
    out_files.insert(0,roi_csv)

    return {
        "roi_csv":roi_csv,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class roi_mean_singleInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_file = File(desc="input file")
    atlas_file = File(desc='atlas file')
    atlas_index = File(desc='atlas index file')

class roi_mean_singleOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    roi_output_dir = traits.String(desc='roi output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class roi_mean_single_pan(BaseInterface):
    input_spec = roi_mean_singleInputSpec
    output_spec = roi_mean_singleOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = roi_mean_single_proc(
            self.inputs.labels_dict,
            self.inputs.input_file,
            self.inputs.atlas_file,
            self.inputs.atlas_index,
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="roi_mean_single_node",input_file="",atlas_file="",atlas_index="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(roi_mean_single_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.input_file = input_file
    pan_node.inputs.atlas_file =  atlas_file
    pan_node.inputs.atlas_index =  atlas_index

    return pan_node


