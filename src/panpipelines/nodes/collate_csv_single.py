from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib

def collate_csv_single_proc(labels_dict, csv_list1,csv_list2, add_prefix):

    cwd=os.getcwd()
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')

    roi_output_dir = os.path.join(cwd,'{}_roi_output_dir'.format(participant_label))
    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    csv_list=[]
    if csv_list1 is not None:
        csv_list.extend(csv_list1)

    if csv_list2 is not None:
        csv_list.extend(csv_list2)

    out_files=[]
    roi_csv = None
    if len(csv_list) > 0:
        cum_table_data = []
        cum_table_columns=[]
        for csv_file in csv_list:
            filenames = os.path.basename(csv_file).split("_")
            if len(filenames) > 3:
                prefix= filenames[1]+"_"+filenames[2]+"."
            elif len(filenames) > 2:
                prefix= filenames[1]+"."
            else:
                prefix= filenames[0]+"."

            if not add_prefix:
                prefix=""

            df = pd.read_table(csv_file,sep=",")
            if df.columns[0] == "subject_id":
                df = df.drop("subject_id",axis=1)
            table_columns = df.columns.tolist()
            table_columns = [prefix+x for x in table_columns]
            cum_table_columns.extend(table_columns)
            cum_table_data.extend(df.values.tolist()[0])

        cum_df = pd.DataFrame([cum_table_data])
        cum_df.columns = cum_table_columns
        cum_df.insert(0,"subject_id",["sub-"+participant_label])

        roi_csv = os.path.join(roi_output_dir,'{}_{}.csv'.format(participant_label,getParams(labels_dict,"COLLATE_NAME")))
        cum_df.to_csv(roi_csv,sep=",",header=True, index=False)

        out_files.insert(0,roi_csv)

    return {
        "roi_csv":roi_csv,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class collate_csv_singleInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    csv_list1 = traits.List(desc='list of files')
    csv_list2 = traits.List(desc='list of files')
    add_prefix = traits.Bool(False,desc="Create header prefix while joining tables",usedefault=True)

class collate_csv_singleOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    roi_output_dir = traits.String(desc='roi output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class collate_csv_single_pan(BaseInterface):
    input_spec = collate_csv_singleInputSpec
    output_spec = collate_csv_singleOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = collate_csv_single_proc(
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


def create(labels_dict,name="collate_csv_single_node",csv_list1="",csv_list2="",add_prefix=False):
    # Create Node
    pan_node = Node(collate_csv_single_pan(), name=name)
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if not csv_list1 is None and not csv_list1 == "":
        pan_node.inputs.csv_list1 = csv_list1
 
    if not csv_list2 is None and not csv_list2 == "":
        pan_node.inputs.csv_list2 = csv_list2

    pan_node.inputs.add_prefix =  add_prefix

    return pan_node


