from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
import pandas as pd

def roi_mean_single_proc(labels_dict,input_file,atlas_file,atlas_index):

    cwd=os.getcwd()
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')

    roi_output_dir = os.path.join(cwd,'{}_roi_output_dir'.format(participant_label))
    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    roi_raw_txt = os.path.join(roi_output_dir,'{}_roi_raw.txt'.format(participant_label))

    params = " -i "+input_file+ \
        " -o "+roi_raw_txt+\
        " --label="+atlas_file

    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmeants"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    with open(atlas_index, 'r') as in_file:
        lines = in_file.readlines()

    table_columns = [x.replace('\n','') for x in lines]
    df2 = pd.read_table(roi_raw_txt,sep=r"\s+",header=None)
    df2.insert(0,"subject_id",["sub-"+participant_label])
    table_columns.insert(0,"subject_id")
    df2.columns = table_columns
    
    roi_csv = os.path.join(roi_output_dir,'{}_{}_{}.csv'.format((participant_label),get_modality(input_file),os.path.basename(atlas_file).split('.')[0]))
    df2.to_csv(roi_csv,sep=",",header=True, index=False)


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


def create(labels_dict,name="roi_mean_single_node",input_file="",atlas_file="",atlas_index=""):
    # Create Node
    pan_node = Node(roi_mean_single_pan(), name=name)
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    if not input_file is None or not input_file == "":
        pan_node.inputs.input_file = input_file

    if atlas_file is None or atlas_file == "":
        atlas_file = getParams(labels_dict,"ATLAS_FILE")
    pan_node.inputs.atlas_file =  atlas_file

    if atlas_index  is None or atlas_index  == "":
        atlas_index = getParams(labels_dict,"ATLAS_INDEX")
    pan_node.inputs.atlas_index =  atlas_index

    return pan_node


