from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
import pandas as pd
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def roi_mean_group_proc(labels_dict,file_template,atlas_file,atlas_index):

    cwd=os.getcwd()
    output_dir=cwd
    # retrieve subject list
    fsldesign_text = getParams(labels_dict,"TEXT_FSL_DESIGN")
    df = pd.read_table(fsldesign_text,sep=",",header=None)

    statsimagestring=''
    stats_image=None
    for subindex in range(len(df)):
        participant_label=df[0][subindex].split('sub-')[1]
        labels_dict = updateParams(labels_dict,'PARTICIPANT_LABEL',participant_label)
        subject_file=getGlob(substitute_labels(getParams(labels_dict,"STAT_FILE_TEMPLATE"),labels_dict))
        statsimagestring= statsimagestring + " " + subject_file 

    if not statsimagestring == "":
        stats_image_dir = os.path.join(cwd,'stats_image')
        if not os.path.isdir(stats_image_dir):
            os.makedirs(stats_image_dir)
        stats_image = os.path.join(stats_image_dir,'stats_image_mni.nii.gz')

        params="-t" \
            " "+ stats_image + \
            " " + statsimagestring 

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmerge"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)


    
    everythingThere=True

    if everythingThere:
        roi_output_dir = os.path.join(cwd,'roi_output_dir')
        if not os.path.isdir(roi_output_dir):
            os.makedirs(roi_output_dir)

        roi_raw_txt = os.path.join(roi_output_dir,'roi_raw.txt')

        params = " -i "+stats_image+ \
            " -o "+roi_raw_txt+\
            " --label="+atlas_file

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmeants"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)


    with open(atlas_index, 'r') as in_file:
        lines = in_file.readlines()

    table_columns = [x.replace('\n','') for x in lines]
    df2 = pd.read_table(roi_raw_txt,sep=r"\s+",header=None)
    df2.insert(0,"subject_id",df[0].tolist())
    table_columns.insert(0,"subject_id")
    df2.columns = table_columns
    
    roi_csv = os.path.join(roi_output_dir,'{}_{}.csv'.format(get_modality(file_template),os.path.basename(atlas_file).split('.')[0]))
    df2.to_csv(roi_csv,sep=",",header=True, index=False)


    out_files=[]
    out_files.insert(0,roi_csv)
    out_files.insert(1,stats_image)

    return {
        "roi_csv":roi_csv,
        "merged_image":stats_image,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class roi_mean_groupInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    file_template = traits.String("",desc="file template", usedefault=True)
    atlas_file = File(desc='atlas file')
    atlas_index = File(desc='atlas index file')

class roi_mean_groupOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    merged_image = File(desc='4D stats image')
    roi_output_dir = traits.String(desc='roi output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class roi_mean_group_pan(BaseInterface):
    input_spec = roi_mean_groupInputSpec
    output_spec = roi_mean_groupOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = roi_mean_group_proc(
            self.inputs.labels_dict,
            self.inputs.file_template,
            self.inputs.atlas_file,
            self.inputs.atlas_index,
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="roi_mean_group_node",file_template="",atlas_file="",atlas_index="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(roi_mean_group_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
            
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if file_template is None or file_template == "":
        file_template = getParams(labels_dict,"STAT_FILE_TEMPLATE")
    pan_node.inputs.file_template =  file_template

    if atlas_file is None or atlas_file == "":
        atlas_file = getParams(labels_dict,"ATLAS_FILE")
    pan_node.inputs.atlas_file =  atlas_file

    if atlas_index  is None or atlas_index  == "":
        atlas_index = getParams(labels_dict,"ATLAS_INDEX")
    pan_node.inputs.atlas_index =  atlas_index

    return pan_node


