from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def collate_csv_single_proc(labels_dict, csv_list1, add_prefix):

    if csv_list1 is None:
        csv_list1 = []

    csv_list=[]
    csv_list.extend(csv_list1)     
    IFLOGGER.info(f"List of csv files to collate: {csv_list}")

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    pipeline = getParams(labels_dict,'PIPELINE')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')

    if not session_label:
        roi_output_dir = os.path.join(cwd,f"{participant_label}_roi_output_dir")
    else:
        roi_output_dir = os.path.join(cwd,f"{participant_label}_{session_label}_roi_output_dir")

    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir,exist_ok=True)

    subject_project = getParams(labels_dict,'PARTICIPANT_XNAT_PROJECT')
    measures_prefixes = getParams(labels_dict,"MEASURES_PREFIXES")
    measures_prefixes_evaluated={}
    if measures_prefixes and isinstance(measures_prefixes,dict):
        for itemkey, itemvalue in measures_prefixes.items():
            measures_prefixes_evaluated[substitute_labels(itemkey,labels_dict)] = substitute_labels(itemvalue,labels_dict)
    else:
        measures_prefixes_evaluated = substitute_labels(measures_prefixes,labels_dict)


    out_files=[]
    roi_csv = None
    custom_prefix=""
    if len(csv_list) > 0:
        cum_table_data = []
        cum_table_columns=[]
        csv_file_count=0
        for csv_file in csv_list:

            if subject_project and subject_project in csv_file:
                creating_pipeline = csv_file.split("/" + subject_project)[0].split("/")[-1]
            else:
                creating_pipeline="default"

            filenames = os.path.basename(csv_file).split("_")
            if len(filenames) > 3:
                prefix= filenames[1]+"_"+filenames[2]
            elif len(filenames) > 2:
                prefix= filenames[1]
            else:
                prefix= filenames[0]

            if measures_prefixes_evaluated:
                if creating_pipeline in measures_prefixes_evaluated.keys():
                    custom_prefix=measures_prefixes_evaluated[creating_pipeline]
                else:
                    custom_prefix=""
            
            elif measures_prefixes_evaluated:
                custom_prefix=measures_prefixes_evaluated

            if not add_prefix:
                if custom_prefix:
                    prefix=custom_prefix +"."
                else:
                    prefix=""
            elif custom_prefix:
                prefix=prefix + "." + custom_prefix +"."
            else:
                prefix=prefix + "."

            df = pd.read_table(csv_file,sep=",")
            if "subject_id" in df.columns:
                df = df.drop("subject_id",axis=1)
            if "session_id" in df.columns:
                df = df.drop("session_id",axis=1)
            if "row_creation_datetime" in df.columns:
                df = df.drop("row_creation_datetime",axis=1)
            table_columns = df.columns.tolist()
            table_columns = [prefix+x for x in table_columns]
            cum_table_columns.extend(table_columns)
            cum_table_data.extend(df.values.tolist()[0])
            csv_file_count = csv_file_count + 1

        cum_df = pd.DataFrame([cum_table_data])
        cum_df.columns = cum_table_columns
        
        # remove duplicates - this is definitely not the most efficient way - so keep an eye on this if dataframes get large
        # https://stackoverflow.com/questions/14984119/python-pandas-remove-duplicate-columns
        cum_df_unique = cum_df.loc[:,~cum_df.columns.duplicated()].copy()
        # sort the columns by name alphabetically
        cum_df_unique = cum_df_unique.reindex(sorted(cum_df_unique.columns), axis=1)


        #process extra columns
        cum_df_unique = processExtraColumns( cum_df_unique, labels_dict)

        if session_label is not None and not session_label == "":
            cum_df_unique.insert(0,"session_id",["ses-"+session_label for x in range(len(cum_df_unique))])
        if participant_label is not None and not participant_label == "":
            cum_df_unique.insert(0,"subject_id",["sub-"+participant_label for x in range(len(cum_df_unique))])

        # Add creation date
        created_datetime = get_datetimestring_utc()
        cum_df_unique.insert(len(cum_df_unique.columns),"row_creation_datetime",[created_datetime for x in range(len(cum_df_unique))])

        collate_name = getParams(labels_dict,"COLLATE_NAME")
        if not collate_name:
            if not pipeline:
                collate_name="csvgroup"
            else:
                collate_name="pipeline"
        
        if not session_label:
            roi_csv = os.path.join(roi_output_dir,f"sub-{participant_label}_{collate_name}.csv")
        else:
            roi_csv = os.path.join(roi_output_dir,f"sub-{participant_label}_ses-{session_label}_{collate_name}.csv")
        cum_df_unique.to_csv(roi_csv,sep=",",header=True, index=False)

        metadata = {}
        metadata = updateParams(metadata,"Title","collate_csv_single.py")
        metadata = updateParams(metadata,"Description","Combine csv files of participant into 1 table.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{csv_list}")
        roi_csv_json = create_metadata(roi_csv, created_datetime, metadata = metadata)

        out_files.insert(0,roi_csv)
        out_files.insert(1,roi_csv_json)

    return {
        "roi_csv":roi_csv,
        "roi_csv_metadata":roi_csv_json,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class collate_csv_singleInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    csv_list1 = traits.List(desc='list of files')
    add_prefix = traits.Bool(False,desc="Create header prefix while joining tables",usedefault=True)

class collate_csv_singleOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    roi_csv_metadata = File(desc='metadata for CSV results file')
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
            self.inputs.add_prefix
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="collate_csv_single_node",csv_list1="",add_prefix=False,LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(collate_csv_single_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if not csv_list1 is None and not csv_list1 == "":
        pan_node.inputs.csv_list1 = csv_list1
 
    pan_node.inputs.add_prefix =  add_prefix

    return pan_node


