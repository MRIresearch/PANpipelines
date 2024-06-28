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
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    
    output_dir=cwd
    participants_label = getParams(labels_dict,'GROUP_PARTICIPANTS_LABEL')
    participants_project = getParams(labels_dict,'GROUP_PARTICIPANTS_XNAT_PROJECT')
    participants_session = getParams(labels_dict,'GROUP_SESSION_LABEL')
    pipeline = getParams(labels_dict,'PIPELINE')

    csv_list_left=[]
    csv_list_right=[]

    if (participants_label is not None and (isinstance(participants_label,list) and len(participants_label) > 1)) and (participants_project is not None and (isinstance(participants_project,list) and len(participants_project)> 1)):
        for part_vals in zip(participants_label,participants_project,participants_session):
            labels_dict = updateParams(labels_dict,"PARTICIPANT_LABEL",part_vals[0])
            labels_dict = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT",part_vals[1])
            labels_dict = updateParams(labels_dict,"PARTICIPANT_SESSION",part_vals[2])
            for meas_template in csv_list1:
                evaluated_meas_template = substitute_labels(meas_template,labels_dict)
                csv_list_left.extend(glob.glob(evaluated_meas_template))
            for meas_template in csv_list2:
                evaluated_meas_template = substitute_labels(meas_template,labels_dict)
                csv_list_right.extend(glob.glob(evaluated_meas_template)) 
    else:
        labels_dict = updateParams(labels_dict,"PARTICIPANT_LABEL","*")
        labels_dict = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT","*")
        labels_dict = updateParams(labels_dict,"PARTICIPANT_SESSION","*")
        for meas_template in csv_list1:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            csv_list_left.extend(glob.glob(evaluated_meas_template))
        for meas_template in csv_list2:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            csv_list_right.extend(glob.glob(evaluated_meas_template))

    csv_list_left = list(set(csv_list_left))
    csv_list_right = list(set(csv_list_right))

    csv_list_left.sort()
    csv_list_right.sort()
    
    roi_output_dir = os.path.join(cwd,'group_roi_output_dir')
    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    IFLOGGER.info(f"List of csv files (left) to collate: {csv_list_left}")
    IFLOGGER.info(f"List of csv files (right) to collate: {csv_list_right}")

    out_files=[]

    roi_csv_inner = None
    cum_df_inner= None
    roi_csv_outer = None
    cum_df_outer= None

    roi_csv_inner_left = None
    roi_csv_outer_left = None
    cum_df_inner_left=pd.DataFrame()
    cum_df_outer_left=pd.DataFrame()

    collate_prefix_left = None
    if len(csv_list_left) > 0:
        for csv_file in csv_list_left:
            df = pd.read_table(csv_file,sep=",")
            if cum_df_inner_left.empty:
                cum_df_inner_left = df
            else:
                cum_df_inner_left = pd.concat([cum_df_inner_left,df],join="inner")

            if cum_df_outer_left.empty:
                cum_df_outer_left = df
            else:
                cum_df_outer_left = pd.concat([cum_df_outer_left,df],join="outer")

        collate_name_left = getParams(labels_dict,"COLLATE_NAME_LEFT")
        if not collate_name_left:
            if not pipeline:
                collate_name_left="csvgroup"
            else:
                collate_name_left="pipeline"

        collate_prefix_left = getParams(labels_dict,"COLLATE_PREFIX_LEFT")

        roi_csv_inner_left = os.path.join(roi_output_dir,'{}_{}_inner_left.csv'.format("group",collate_name_left))
        roi_csv_outer_left = os.path.join(roi_output_dir,'{}_{}_outer_left.csv'.format("group",collate_name_left))

        #create sorted output
        cum_df_inner_left = cum_df_inner_left.reindex(sorted(cum_df_inner_left.columns), axis=1)
        if "session_id" in cum_df_inner_left.columns and "subject_id" in cum_df_inner_left.columns:
            sub_col = cum_df_inner_left.pop("subject_id")
            ses_col = cum_df_inner_left.pop("session_id")

            if collate_prefix_left:
                orig_cols = cum_df_inner_left.columns.tolist()
                new_cols = [f"{collate_prefix_left}.{x}" for x in orig_cols]
                new_dict = dict(zip(orig_cols,new_cols))
                cum_df_inner_left = cum_df_inner_left.rename(columns=new_dict)

            cum_df_inner_left.insert(0,"session_id",ses_col)
            cum_df_inner_left.insert(0,"subject_id",sub_col)
        elif collate_prefix_left:
                orig_cols = cum_df_inner_left.columns.tolist()
                new_cols = [f"{collate_prefix_left}.{x}" for x in orig_cols]
                new_dict = dict(zip(orig_cols,new_cols))
                cum_df_inner_left = cum_df_inner_left.rename(columns=new_dict)

        #create sorted output
        cum_df_outer_left = cum_df_outer_left.reindex(sorted(cum_df_outer_left.columns), axis=1)
        if "session_id" in cum_df_outer_left.columns and "subject_id" in cum_df_outer_left.columns:
            sub_col = cum_df_outer_left.pop("subject_id")
            ses_col = cum_df_outer_left.pop("session_id")

            if collate_prefix_left:
                orig_cols = cum_df_outer_left.columns.tolist()
                new_cols = [f"{collate_prefix_left}.{x}" for x in orig_cols]
                new_dict = dict(zip(orig_cols,new_cols))
                cum_df_outer_left = cum_df_outer_left.rename(columns=new_dict)

            cum_df_outer_left.insert(0,"session_id",ses_col)
            cum_df_outer_left.insert(0,"subject_id",sub_col)
        elif collate_prefix_left:
            orig_cols = cum_df_outer_left.columns.tolist()
            new_cols = [f"{collate_prefix_left}.{x}" for x in orig_cols]
            new_dict = dict(zip(orig_cols,new_cols))
            cum_df_outer_left = cum_df_outer_left.rename(columns=new_dict)

        cum_df_inner_left.to_csv(roi_csv_inner_left,sep=",",header=True, index=False)
        cum_df_outer_left.to_csv(roi_csv_outer_left,sep=",",header=True, index=False)

        metadata = {}
        roi_csv_inner_left_json = os.path.splitext(roi_csv_inner_left)[0] + ".json"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Inner Join (left hand table)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_inner_left_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv_inner_left}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{csv_list_left}")
        export_labels(metadata,roi_csv_inner_left_json)

        metadata = {}
        roi_csv_outer_left_json = os.path.splitext(roi_csv_outer_left)[0] + ".json"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Outer Join (eft hand table)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_outer_left_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv_outer_left}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{csv_list_left}")
        export_labels(metadata,roi_csv_outer_left_json)

    roi_csv_inner_right = None
    roi_csv_outer_right = None
    cum_df_inner_right=pd.DataFrame()
    cum_df_outer_right=pd.DataFrame()
    collate_prefix_right=None
    if len(csv_list_right) > 0:
        for csv_file in csv_list_right:
            df = pd.read_table(csv_file,sep=",")
            if cum_df_inner_right.empty:
                cum_df_inner_right = df
            else:
                cum_df_inner_right = pd.concat([cum_df_inner_right,df],join="inner")

            if cum_df_outer_right.empty:
                cum_df_outer_right = df
            else:
                cum_df_outer_right = pd.concat([cum_df_outer_right,df],join="outer")

        collate_name_right = getParams(labels_dict,"COLLATE_NAME_RIGHT")
        if not collate_name_right:
            if not pipeline:
                collate_name_right="csvgroup"
            else:
                collate_name_right="pipeline"

        collate_prefix_right = getParams(labels_dict,"COLLATE_PREFIX_RIGHT")

        roi_csv_inner_right = os.path.join(roi_output_dir,'{}_{}_inner_right.csv'.format("group",collate_name_right))
        roi_csv_outer_right = os.path.join(roi_output_dir,'{}_{}_outer_right.csv'.format("group",collate_name_right))

        #create sorted output
        cum_df_inner_right = cum_df_inner_right.reindex(sorted(cum_df_inner_right.columns), axis=1)
        if "session_id" in cum_df_inner_right.columns and "subject_id" in cum_df_inner_right.columns:
            sub_col = cum_df_inner_right.pop("subject_id")
            ses_col = cum_df_inner_right.pop("session_id")

            if collate_prefix_right:
                orig_cols = cum_df_inner_right.columns.tolist()
                new_cols = [f"{collate_prefix_right}.{x}" for x in orig_cols]
                new_dict = dict(zip(orig_cols,new_cols))
                cum_df_inner_right = cum_df_inner_right.rename(columns=new_dict)

            cum_df_inner_right.insert(0,"session_id",ses_col)
            cum_df_inner_right.insert(0,"subject_id",sub_col)

        elif collate_prefix_right:
            orig_cols = cum_df_inner_right.columns.tolist()
            new_cols = [f"{collate_prefix_right}.{x}" for x in orig_cols]
            new_dict = dict(zip(orig_cols,new_cols))
            cum_df_inner_right = cum_df_inner_right.rename(columns=new_dict)

        #create sorted output
        cum_df_outer_right = cum_df_outer_right.reindex(sorted(cum_df_outer_right.columns), axis=1)
        if "session_id" in cum_df_outer_right.columns and "subject_id" in cum_df_outer_right.columns:
            sub_col = cum_df_outer_right.pop("subject_id")
            ses_col = cum_df_outer_right.pop("session_id")

            if collate_prefix_right:
                orig_cols = cum_df_outer_right.columns.tolist()
                new_cols = [f"{collate_prefix_right}.{x}" for x in orig_cols]
                new_dict = dict(zip(orig_cols,new_cols))
                cum_df_outer_right = cum_df_outer_right.rename(columns=new_dict)

            cum_df_outer_right.insert(0,"session_id",ses_col)
            cum_df_outer_right.insert(0,"subject_id",sub_col)
        elif collate_prefix_right:
            orig_cols = cum_df_outer_right.columns.tolist()
            new_cols = [f"{collate_prefix_right}.{x}" for x in orig_cols]
            new_dict = dict(zip(orig_cols,new_cols))
            cum_df_outer_right = cum_df_outer_right.rename(columns=new_dict)

        cum_df_inner_right.to_csv(roi_csv_inner_right,sep=",",header=True, index=False)
        cum_df_outer_right.to_csv(roi_csv_outer_right,sep=",",header=True, index=False)

        metadata = {}
        roi_csv_inner_right_json = os.path.splitext(roi_csv_inner_right)[0] + ".json"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Inner Join (right hand table)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_inner_right_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv_inner_right}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{csv_list_right}")
        export_labels(metadata,roi_csv_inner_right_json)

        metadata = {}
        roi_csv_outer_right_json = os.path.splitext(roi_csv_outer_right)[0] + ".json"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Outer Join (eft hand table)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_outer_right_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv_outer_right}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{csv_list_right}")
        export_labels(metadata,roi_csv_outer_right_json)

    collate_join_left= getParams(labels_dict,"COLLATECOLS_JOIN_LEFT")
    if not collate_join_left:
        collate_join_left=["subject_id","session_id"]
    elif collate_prefix_left:
        collate_join_left = [f"{collate_prefix_left}.{x}" if  f"{collate_prefix_left}." not in x and x != "subject_id" and x != "session_id" else x for x in collate_join_left ]

    collate_join_right= getParams(labels_dict,"COLLATECOLS_JOIN_RIGHT")
    if not collate_join_right:
        collate_join_right=["subject_id","session_id"]
    elif collate_prefix_right:
        collate_join_right = [f"{collate_prefix_right}.{x}" if  f"{collate_prefix_right}." not in x and x != "subject_id" and x != "session_id" else x for x in collate_join_right ]


    if not cum_df_inner_right.empty and not cum_df_inner_left.empty:
        cum_df_inner = pd.merge(cum_df_inner_left, cum_df_inner_right,  how='left', left_on=collate_join_left, right_on =collate_join_right)
        roi_csv_inner = os.path.join(roi_output_dir,'{}_{}-{}_inner.csv'.format("final-group",collate_name_left,collate_name_right))

        #create sorted output
        cum_df_inner = cum_df_inner.reindex(sorted(cum_df_inner.columns), axis=1)
        if "session_id" in cum_df_inner.columns and "subject_id" in cum_df_inner.columns:
            sub_col = cum_df_inner.pop("subject_id")
            ses_col = cum_df_inner.pop("session_id")

            cum_df_inner.insert(0,"session_id",ses_col)
            cum_df_inner.insert(0,"subject_id",sub_col)

        cum_df_inner.to_csv(roi_csv_inner,sep=",",header=True, index=False)
        metadata = {}
        roi_csv_inner_json = os.path.splitext(roi_csv_inner)[0] + ".json"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Inner Join (both tables)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_inner_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv_inner}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_inner_left},{roi_csv_inner_right}")
        export_labels(metadata,roi_csv_inner_json)
        out_files.insert(0,roi_csv_inner_left)
        out_files.insert(1,roi_csv_inner_right)
    elif not cum_df_inner_right.empty:
        roi_csv_inner = roi_csv_inner_right
        out_files.insert(0,roi_csv_inner_right)
    elif not cum_df_inner_left.empty:
        roi_csv_inner = roi_csv_inner_left
        out_files.insert(0,roi_csv_inner_left)

    if not cum_df_outer_right.empty and not cum_df_outer_left.empty:
        cum_df_outer = pd.merge(cum_df_outer_left, cum_df_outer_right,  how='left', left_on=collate_join_left, right_on =collate_join_right)
        roi_csv_outer = os.path.join(roi_output_dir,'{}_{}-{}_outer.csv'.format("final-group",collate_name_left,collate_name_right))

        #create sorted output
        cum_df_outer = cum_df_outer.reindex(sorted(cum_df_outer.columns), axis=1)
        if "session_id" in cum_df_outer.columns and "subject_id" in cum_df_outer.columns:
            sub_col = cum_df_outer.pop("subject_id")
            ses_col = cum_df_outer.pop("session_id")
            cum_df_outer.insert(0,"session_id",ses_col)
            cum_df_outer.insert(0,"subject_id",sub_col)

        cum_df_outer.to_csv(roi_csv_outer,sep=",",header=True, index=False)
        metadata = {}
        roi_csv_outer_json = os.path.splitext(roi_csv_outer)[0] + ".json"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Outer Join (both tables)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_outer_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv_outer}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_outer_left},{roi_csv_outer_right}")
        export_labels(metadata,roi_csv_outer_json)
        out_files.insert(0,roi_csv_outer_left)
        out_files.insert(1,roi_csv_outer_right)
    elif not cum_df_outer_right.empty:
        roi_csv_outer = roi_csv_outer_right
        out_files.insert(0,roi_csv_outer_right)
    elif not cum_df_outer_left.empty:
        roi_csv_outer = roi_csv_outer_left
        out_files.insert(0,roi_csv_outer_left)

    out_files.insert(0,roi_csv_inner)
    out_files.insert(1,roi_csv_outer)

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


