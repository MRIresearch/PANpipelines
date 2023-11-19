from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def collate_csv_group_proc(labels_dict, csv_list1,csv_list2, add_prefix):

    if csv_list1 is None:
        csv_list1 = []
    if csv_list2 is None:
        csv_list2 = []
        
    cwd=os.getcwd()
    output_dir=cwd
    participants_label = getParams(labels_dict,'PARTICIPANTS_LABEL')
    participants_project = getParams(labels_dict,'PARTICIPANTS_XNAT_PROJECT')
    pipeline = getParams(labels_dict,'PIPELINE')

    csv_list=[]

    if (participants_label is not None and (isinstance(participants_label,list) and len(participants_label) > 1)) and (participants_project is not None and (isinstance(participants_project,list) and len(participants_project)> 1)):
        for part_vals in zip(participants_label,participants_project):
            panpipe_labels = updateParams(labels_dict,"PARTICIPANT_LABEL",part_vals[0])
            panpipe_labels = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT",part_vals[1])
            for meas_template in csv_list1:
                evaluated_meas_template = substitute_labels(meas_template,labels_dict)
                csv_list.extend(glob.glob(evaluated_meas_template))
            for meas_template in csv_list2:
                evaluated_meas_template = substitute_labels(meas_template,labels_dict)
                csv_list.extend(glob.glob(evaluated_meas_template)) 
    else:
        panpipe_labels = updateParams(labels_dict,"PARTICIPANT_LABEL","*")
        panpipe_labels = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT","*")
        for meas_template in csv_list1:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            csv_list.extend(glob.glob(evaluated_meas_template))
        for meas_template in csv_list2:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            csv_list.extend(glob.glob(evaluated_meas_template))

    csv_list.sort()
    
    roi_output_dir = os.path.join(cwd,'group_roi_output_dir')
    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    IFLOGGER.info(f"List of csv files to collate: {csv_list}")

    out_files=[]
    roi_csv_inner = None
    roi_csv_outer = None
    cum_df_inner=pd.DataFrame()
    cum_df_outer=pd.DataFrame()
    if len(csv_list) > 0:
        for csv_file in csv_list:
            df = pd.read_table(csv_file,sep=",")
            if cum_df_inner.empty:
                cum_df_inner = df
            else:
                cum_df_inner = pd.concat([cum_df_inner,df],join="inner")

            if cum_df_outer.empty:
                cum_df_outer = df
            else:
                cum_df_outer = pd.concat([cum_df_outer,df],join="outer")

        collate_name = getParams(labels_dict,"COLLATE_NAME")
        if not collate_name:
            if not pipeline:
                collate_name="csvgroup"
            else:
                collate_name="pipeline"

        roi_csv_inner = os.path.join(roi_output_dir,'{}_{}_inner.csv'.format("group",collate_name))
        roi_csv_outer = os.path.join(roi_output_dir,'{}_{}_outer.csv'.format("group",collate_name))

        cum_df_inner.to_csv(roi_csv_inner,sep=",",header=True, index=False)
        cum_df_outer.to_csv(roi_csv_outer,sep=",",header=True, index=False)

        out_files.insert(0,roi_csv_inner)
        out_files.insert(0,roi_csv_outer)

    return {
        "roi_csv_inner":roi_csv_inner,
        "roi_csv_outer":roi_csv_outer,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }


class collate_csv_groupInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    csv_list1 = traits.List(desc='list of files')
    csv_list2 = traits.List(desc='list of files')
    add_prefix = traits.Bool(False,desc="Create header prefix while joining tables",usedefault=True)

class collate_csv_groupOutputSpec(TraitedSpec):
    roi_csv_inner = File(desc='CSV file of results')
    roi_csv_outer = File(desc='CSV file of results')
    roi_output_dir = traits.String(desc='roi output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class collate_csv_group_pan(BaseInterface):
    input_spec = collate_csv_groupInputSpec
    output_spec = collate_csv_groupOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = collate_csv_group_proc(
            self.inputs.labels_dict,
            self.inputs.csv_list1,
            self.inputs.csv_list2,
            self.inputs.add_prefix
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="collate_csv_group_node",csv_list1="",csv_list2="",add_prefix=False,LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(collate_csv_group_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if not csv_list1 is None and not csv_list1 == "":
        pan_node.inputs.csv_list1 = csv_list1
 
    if not csv_list2 is None and not csv_list2 == "":
        pan_node.inputs.csv_list2 = csv_list2

    pan_node.inputs.add_prefix =  add_prefix

    return pan_node


