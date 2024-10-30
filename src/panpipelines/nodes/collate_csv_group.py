from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
from nipype import logging as nlogging
import shutil

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

    participant_exclusions = getParams(labels_dict,"EXCLUDED_PARTICIPANTS")
    if participant_exclusions:
        subject_exclusions = process_exclusions(participant_exclusions)
    else:
        subject_exclusions = []

    RSEP = getParams(labels_dict,'RSEP')
    if not RSEP:
        RSEP=","
    LSEP = getParams(labels_dict,'LSEP')
    if not LSEP:
        LSEP=","

    csv_list_left=[]
    csv_list_right=[]

    EXPAND_CSV1=False
    if len(csv_list1)>0:
        for meas_template in csv_list1:
            if "<PARTICIPANT_LABEL>" in meas_template:
                EXPAND_CSV1=True
                break

    EXPAND_CSV2=False
    if len(csv_list2)>0:
        for meas_template in csv_list2:
            if "<PARTICIPANT_LABEL>" in meas_template:
                EXPAND_CSV2=True
                break

    if (participants_label is not None and (isinstance(participants_label,list) and len(participants_label) > 1)) and (participants_project is not None and (isinstance(participants_project,list) and len(participants_project)> 1)) and (EXPAND_CSV1 or EXPAND_CSV2):
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
    elif (EXPAND_CSV1 or EXPAND_CSV2):
        labels_dict = updateParams(labels_dict,"PARTICIPANT_LABEL","*")
        labels_dict = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT","*")
        labels_dict = updateParams(labels_dict,"PARTICIPANT_SESSION","*")
        for meas_template in csv_list1:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            csv_list_left.extend(glob.glob(evaluated_meas_template))
        for meas_template in csv_list2:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            csv_list_right.extend(glob.glob(evaluated_meas_template))
    else:
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

    collate_prefix_left = getParams(labels_dict,"COLLATE_PREFIX_LEFT")
    if not collate_prefix_left:
        collate_prefix_left = None

    collate_prefix_right = getParams(labels_dict,"COLLATE_PREFIX_RIGHT")
    if not collate_prefix_right:
        collate_prefix_right=None

    collate_join_left= getParams(labels_dict,"COLLATECOLS_JOIN_LEFT")
    if not collate_join_left:
        collate_join_left=["subject_id","session_id"]

    collate_join_right= getParams(labels_dict,"COLLATECOLS_JOIN_RIGHT")
    if not collate_join_right:
        collate_join_right=["subject_id","session_id"]
 
    len_csv_list_left = len(csv_list_left) 
    if len_csv_list_left > 0:
        for csv_file_index, csv_file in enumerate(csv_list_left):
            df = pd.read_table(csv_file,sep=LSEP)
            if cum_df_inner_left.empty:
                cum_df_inner_left = df
            elif csv_file_index == len_csv_list_left - 1:
                cum_df_inner_left = pd.concat([cum_df_inner_left,df],join="inner").drop_duplicates(ignore_index=True)
            else:
                cum_df_inner_left = pd.concat([cum_df_inner_left,df],join="inner")

            if cum_df_outer_left.empty:
                cum_df_outer_left = df
            elif csv_file_index == len_csv_list_left - 1:
                cum_df_outer_left = pd.concat([cum_df_outer_left,df],join="outer").drop_duplicates(ignore_index=True)
            else:
                cum_df_outer_left = pd.concat([cum_df_outer_left,df],join="outer")

        collate_name_left = getParams(labels_dict,"COLLATE_NAME_LEFT")
        if not collate_name_left:
            if not pipeline:
                collate_name_left="csvgroup"
            else:
                collate_name_left=f"{pipeline}"

        roi_csv_inner_left = os.path.join(roi_output_dir,'{}_{}_inner_left.csv'.format("group",collate_name_left))
        roi_csv_outer_left = os.path.join(roi_output_dir,'{}_{}_outer_left.csv'.format("group",collate_name_left))

        #create sorted output
        cum_df_inner_left = cum_df_inner_left.reindex(sorted(cum_df_inner_left.columns), axis=1)

        if collate_prefix_left:
            orig_cols = cum_df_inner_left.columns.tolist()
            other_cols = [x for x in orig_cols if x not in collate_join_left]
            new_cols = [f"{collate_prefix_left}.{x}" for x in other_cols]
            new_dict = dict(zip(other_cols,new_cols))
            cum_df_inner_left = cum_df_inner_left.rename(columns=new_dict)

        index_col_list = [collate_join_left.index(x) for x in cum_df_inner_left.columns if x in collate_join_left]
        index_col_list.sort()
        for index_col_num in index_col_list:
            index_col = cum_df_inner_left.pop(collate_join_left[index_col_num])
            cum_df_inner_left.insert(index_col_num,collate_join_left[index_col_num],index_col)


        #create sorted output
        cum_df_outer_left = cum_df_outer_left.reindex(sorted(cum_df_outer_left.columns), axis=1)
        if collate_prefix_left:
            orig_cols = cum_df_outer_left.columns.tolist()
            other_cols = [x for x in orig_cols if x not in collate_join_left]
            new_cols = [f"{collate_prefix_left}.{x}" for x in other_cols]
            new_dict = dict(zip(other_cols,new_cols))
            cum_df_outer_left = cum_df_outer_left.rename(columns=new_dict)

        index_col_list = [collate_join_left.index(x) for x in cum_df_outer_left.columns if x in collate_join_left]
        index_col_list.sort()
        for index_col_num in index_col_list:
            index_col = cum_df_outer_left.pop(collate_join_left[index_col_num])
            cum_df_outer_left.insert(index_col_num,collate_join_left[index_col_num],index_col)


        # deal with excluded
        cum_df_inner_left = mask_excludedrows(cum_df_inner_left, subject_exclusions, collate_join_left)
        cum_df_inner_left.to_csv(roi_csv_inner_left,sep=",",header=True, index=False)

        cum_df_outer_left = mask_excludedrows(cum_df_outer_left, subject_exclusions, collate_join_left)
        cum_df_outer_left.to_csv(roi_csv_outer_left,sep=",",header=True, index=False)

        # Drop or rename columns as specififed by LEFT_DROP and LEFT_RENAME
        left_inner_cols=list(cum_df_inner_left.columns.values)
        left_outer_cols=list(cum_df_outer_left.columns.values)
        LEFT_DROP = getParams(labels_dict,"LEFT_DROP")
        if LEFT_DROP:
            LEFT_COL_INNER=False
            LEFT_COL_OUTER=False
            if not isinstance(LEFT_DROP,list):
                LEFT_DROP=[LEFT_DROP]
            left_inner_cols=list(cum_df_inner_left.columns.values)
            left_outer_cols=list(cum_df_outer_left.columns.values)
            for col_drop in LEFT_DROP:
                if col_drop in left_inner_cols:
                    IFLOGGER.debug(f"about to drop {col_drop} from left_inner_cols")
                    left_inner_cols.pop(left_inner_cols.index(col_drop))
                    LEFT_COL_INNER = True

                if col_drop in left_outer_cols:
                    IFLOGGER.debug(f"about to drop {col_drop} from left_outer_cols")
                    left_outer_cols.pop(left_outer_cols.index(col_drop))
                    LEFT_COL_OUTER = True

            if LEFT_COL_INNER:
                cum_df_inner_left=cum_df_inner_left[left_inner_cols]
                IFLOGGER.debug(f"Created cum_df_inner_left with columns {left_inner_cols}")

            if LEFT_COL_OUTER:
                cum_df_outer_left=cum_df_outer_left[left_outer_cols]
                IFLOGGER.debug(f"Created cum_df_outer_left with columns {left_outer_cols}")

        LEFT_RENAME = getParams(labels_dict,"LEFT_RENAME")
        if LEFT_RENAME:
            left_inner_dict={}
            left_outer_dict={}
            if isinstance(LEFT_RENAME,dict):
                for itemkey,itemvalue in LEFT_RENAME.items():
                    if itemkey in left_inner_cols:
                        left_inner_dict[itemkey]=itemvalue
                    else:
                        IFLOGGER.debug(f"Column {itemkey} not found in left_inner_cols {left_inner_cols}. Skipping this rename {itemkey}:{itemvalue}")

                    if itemkey in left_outer_cols:
                        left_outer_dict[itemkey]=itemvalue
                    else:
                        IFLOGGER.debug(f"Column {itemkey} not found in left_inner_cols {left_outer_cols}. Skipping this rename {itemkey}:{itemvalue}")

                if left_inner_dict:
                    cum_df_inner_left = cum_df_inner_left.rename(columns=left_inner_dict)

                if left_outer_dict:
                    cum_df_outer_left = cum_df_outer_left.rename(columns=left_outer_dict)


            else:
                IFLOGGER.debug(f"LEFT_RENAME should be a dictionary of values but {LEFT_RENAME} passed")
                


    roi_csv_inner_right = None
    roi_csv_outer_right = None
    cum_df_inner_right=pd.DataFrame()
    cum_df_outer_right=pd.DataFrame()

    len_csv_list_right = len(csv_list_right)
    if  len_csv_list_right > 0:
        for csv_file_index, csv_file in enumerate(csv_list_right):
            df = pd.read_table(csv_file,sep=RSEP)
            if cum_df_inner_right.empty:
                cum_df_inner_right = df
            elif csv_file_index == len_csv_list_right - 1:
                cum_df_inner_right = pd.concat([cum_df_inner_right,df],join="inner").drop_duplicates(ignore_index=True)
            else:
                cum_df_inner_right = pd.concat([cum_df_inner_right,df],join="inner")

            if cum_df_outer_right.empty:
                cum_df_outer_right = df
            elif csv_file_index == len_csv_list_right - 1:
                cum_df_outer_right = pd.concat([cum_df_outer_right,df],join="outer").drop_duplicates(ignore_index=True)
            else:
                cum_df_outer_right = pd.concat([cum_df_outer_right,df],join="outer")

        collate_name_right = getParams(labels_dict,"COLLATE_NAME_RIGHT")
        if not collate_name_right:
            if not pipeline:
                collate_name_right="csvgroup"
            else:
                collate_name_right="pipeline"


        roi_csv_inner_right = os.path.join(roi_output_dir,'{}_{}_inner_right.csv'.format("group",collate_name_right))
        roi_csv_outer_right = os.path.join(roi_output_dir,'{}_{}_outer_right.csv'.format("group",collate_name_right))

        #create sorted output
        cum_df_inner_right = cum_df_inner_right.reindex(sorted(cum_df_inner_right.columns), axis=1)
        if collate_prefix_right:
            orig_cols = cum_df_inner_right.columns.tolist()
            other_cols = [x for x in orig_cols if x not in collate_join_right]
            new_cols = [f"{collate_prefix_right}.{x}" for x in other_cols]
            new_dict = dict(zip(other_cols,new_cols))
            cum_df_inner_right = cum_df_inner_right.rename(columns=new_dict)

        index_col_list = [collate_join_right.index(x) for x in cum_df_inner_right.columns if x in collate_join_right]
        index_col_list.sort()
        for index_col_num in index_col_list:
            index_col = cum_df_inner_right.pop(collate_join_right[index_col_num])
            cum_df_inner_right.insert(index_col_num,collate_join_right[index_col_num],index_col)

        #create sorted output
        cum_df_outer_right = cum_df_outer_right.reindex(sorted(cum_df_outer_right.columns), axis=1)
        if collate_prefix_right:
            orig_cols = cum_df_outer_right.columns.tolist()
            other_cols = [x for x in orig_cols if x not in collate_join_right]
            new_cols = [f"{collate_prefix_right}.{x}" for x in other_cols]
            new_dict = dict(zip(other_cols,new_cols))
            cum_df_outer_right = cum_df_outer_right.rename(columns=new_dict)

        index_col_list = [collate_join_right.index(x) for x in cum_df_outer_right.columns if x in collate_join_right]
        index_col_list.sort()
        for index_col_num in index_col_list:
            index_col = cum_df_outer_right.pop(collate_join_right[index_col_num])
            cum_df_outer_right.insert(index_col_num,collate_join_right[index_col_num],index_col)


        cum_df_inner_right = mask_excludedrows(cum_df_inner_right, subject_exclusions, collate_join_right)     
        cum_df_inner_right.to_csv(roi_csv_inner_right,sep=",",header=True, index=False)

        cum_df_outer_right = mask_excludedrows(cum_df_outer_right, subject_exclusions, collate_join_right)
        cum_df_outer_right.to_csv(roi_csv_outer_right,sep=",",header=True, index=False)

        # Drop or rename columns as specififed by RIGHT_DROP and RIGHT_RENAME
        right_inner_cols=list(cum_df_inner_right.columns.values)
        right_outer_cols=list(cum_df_outer_right.columns.values)
        RIGHT_DROP = getParams(labels_dict,"RIGHT_DROP")
        if RIGHT_DROP:
            RIGHT_COL_INNER=False
            RIGHT_COL_OUTER=False
            if not isinstance(RIGHT_DROP,list):
                RIGHT_DROP=[RIGHT_DROP]
            right_inner_cols=list(cum_df_inner_right.columns.values)
            right_outer_cols=list(cum_df_outer_right.columns.values)
            for col_drop in RIGHT_DROP:
                if col_drop in right_inner_cols:
                    IFLOGGER.debug(f"about to drop {col_drop} from right_inner_cols")
                    right_inner_cols.pop(right_inner_cols.index(col_drop))
                    RIGHT_COL_INNER = True

                if col_drop in right_outer_cols:
                    IFLOGGER.debug(f"about to drop {col_drop} from right_outer_cols")
                    right_outer_cols.pop(right_outer_cols.index(col_drop))
                    RIGHT_COL_OUTER = True

            if RIGHT_COL_INNER:
                cum_df_inner_right=cum_df_inner_right[right_inner_cols]
                IFLOGGER.debug(f"Created cum_df_inner_right with columns {right_inner_cols}")

            if RIGHT_COL_OUTER:
                cum_df_outer_right=cum_df_outer_right[right_outer_cols]
                IFLOGGER.debug(f"Created cum_df_outer_right with columns {right_outer_cols}")

        RIGHT_RENAME = getParams(labels_dict,"RIGHT_RENAME")
        if RIGHT_RENAME:
            right_inner_dict={}
            right_outer_dict={}
            if isinstance(RIGHT_RENAME,dict):
                for itemkey,itemvalue in RIGHT_RENAME.items():
                    if itemkey in right_inner_cols:
                        right_inner_dict[itemkey]=itemvalue
                    else:
                        IFLOGGER.debug(f"Column {itemkey} not found in right_inner_cols {right_inner_cols}. Skipping this rename {itemkey}:{itemvalue}")

                    if itemkey in right_outer_cols:
                        right_outer_dict[itemkey]=itemvalue
                    else:
                        IFLOGGER.debug(f"Column {itemkey} not found in right_inner_cols {right_outer_cols}. Skipping this rename {itemkey}:{itemvalue}")

                if right_inner_dict:
                    cum_df_inner_right = cum_df_inner_right.rename(columns=right_inner_dict)

                if right_outer_dict:
                    cum_df_outer_right = cum_df_outer_right.rename(columns=right_outer_dict)


            else:
                IFLOGGER.debug(f"RIGHT_RENAME should be a dictionary of values but {RIGHT_RENAME} passed")


    if not cum_df_inner_right.empty and not cum_df_inner_left.empty:

        # if a column is duplicated in left and right then quick hack is to just remove it from the right table, except for the join columns
        left_inner_cols=list(cum_df_inner_left.columns.values)
        right_inner_cols=list(cum_df_inner_right.columns.values)
        right_inner_cols_to_drop = set(left_inner_cols).intersection(set(right_inner_cols)).difference(set(collate_join_right))
        IFLOGGER.info(f"Dropping duplicated columns {right_inner_cols_to_drop} from right table")
        cum_df_inner_right = cum_df_inner_right.drop(right_inner_cols_to_drop, axis=1)

        cum_df_inner = pd.merge(cum_df_inner_left, cum_df_inner_right,  how='left', left_on=collate_join_left, right_on =collate_join_right)
        roi_csv_inner = os.path.join(roi_output_dir,'{}_{}-{}_inner.csv'.format("final-group",collate_name_left,collate_name_right))

        #create sorted output
        cum_df_inner = cum_df_inner.reindex(sorted(cum_df_inner.columns), axis=1)
        index_col_list = [collate_join_left.index(x) for x in cum_df_inner.columns if x in collate_join_left]
        index_col_list.sort()
        for index_col_num in index_col_list:
            index_col = cum_df_inner.pop(collate_join_left[index_col_num])
            cum_df_inner.insert(index_col_num,collate_join_left[index_col_num],index_col)


        cum_df_inner.to_csv(roi_csv_inner,sep=",",header=True, index=False)

        metadata = {}
        created_datetime = get_datetimestring_utc()
        metadata["History"]={}
        metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Inner Join (both tables)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_inner_left},{roi_csv_inner_right}")
        roi_csv_inner_json = create_metadata(roi_csv_inner, created_datetime, metadata = metadata)

    elif not cum_df_inner_right.empty:
        roi_csv_inner = roi_csv_inner_right
        metadata = {}
        created_datetime = get_datetimestring_utc()
        metadata["History"]={}
        metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: collate single table without join")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_inner_left},{roi_csv_inner_right}")
        roi_csv_inner_json = create_metadata(roi_csv_inner, created_datetime, metadata = metadata)

    elif not cum_df_inner_left.empty:
        roi_csv_inner = roi_csv_inner_left
        metadata = {}
        created_datetime = get_datetimestring_utc()
        metadata["History"]={}
        metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: collate single table without join")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_inner_left},{roi_csv_inner_right}")
        roi_csv_inner_json = create_metadata(roi_csv_inner, created_datetime, metadata = metadata)

    if not cum_df_outer_right.empty and not cum_df_outer_left.empty:

        # if a column is duplicated in left and right then quick hack is to just remove it from the right table, except for the join columns
        left_outer_cols=list(cum_df_outer_left.columns.values)
        right_outer_cols=list(cum_df_outer_right.columns.values)
        right_outer_cols_to_drop = set(left_outer_cols).intersection(set(right_outer_cols)).difference(set(collate_join_right))
        IFLOGGER.info(f"Dropping duplicated columns {right_outer_cols_to_drop} from right table")
        cum_df_outer_right = cum_df_outer_right.drop(right_outer_cols_to_drop, axis=1)

        cum_df_outer = pd.merge(cum_df_outer_left, cum_df_outer_right,  how='left', left_on=collate_join_left, right_on =collate_join_right)
        roi_csv_outer = os.path.join(roi_output_dir,'{}_{}-{}_outer.csv'.format("final-group",collate_name_left,collate_name_right))

        #create sorted output
        cum_df_outer = cum_df_outer.reindex(sorted(cum_df_outer.columns), axis=1)

        index_col_list = [collate_join_left.index(x) for x in cum_df_outer.columns if x in collate_join_left]
        index_col_list.sort()
        for index_col_num in index_col_list:
            index_col = cum_df_outer.pop(collate_join_left[index_col_num])
            cum_df_outer.insert(index_col_num,collate_join_left[index_col_num],index_col)

        cum_df_outer.to_csv(roi_csv_outer,sep=",",header=True, index=False)
        metadata = {}
        created_datetime = get_datetimestring_utc()
        metadata["History"]={}
        metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: Outer Join (both tables)")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_outer_left},{roi_csv_outer_right}")
        roi_csv_outer_json = create_metadata(roi_csv_outer, created_datetime, metadata = metadata)


    elif not cum_df_outer_right.empty:
        roi_csv_outer = roi_csv_outer_right
        metadata = {}
        created_datetime = get_datetimestring_utc()
        metadata["History"]={}
        metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: collate single table without join")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_outer}")
        roi_csv_outer_json = create_metadata(roi_csv_outer, created_datetime, metadata = metadata)
    elif not cum_df_outer_left.empty:
        roi_csv_outer = roi_csv_outer_left
        metadata = {}
        created_datetime = get_datetimestring_utc()
        metadata["History"]={}
        metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
        metadata = updateParams(metadata,"Title","collate_csv_group.py: collate single table without join")
        metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
        metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
        metadata = updateParams(metadata,"InputFiles",f"{roi_csv_outer}")
        roi_csv_outer_json = create_metadata(roi_csv_outer, created_datetime, metadata = metadata)


    ALL_GROUP = isTrue(getParams(labels_dict,"ALL_GROUP"))
    LAST_OUTPUT_FILES = getParams(labels_dict,"LAST_OUTPUT_FILES")
    if not ALL_GROUP and LAST_OUTPUT_FILES:
        IFLOGGER.info("This is an update to the last group files. We will append results from this run to files at {LAST_OUTPUT_FILES}")
        for group_file in LAST_OUTPUT_FILES:

            if os.path.basename(group_file) == os.path.basename(roi_csv_inner):
                new_cum_df_inner = pd.DataFrame()
                group_df = pd.read_table(group_file,sep=LSEP)
                new_df = pd.read_table(roi_csv_inner,sep=LSEP)
                new_cum_df_inner = pd.concat([group_df,new_df],join="inner").drop_duplicates(ignore_index=True)

                if new_cum_df_inner.empty:
                    IFLOGGER.info("Problem reading files {group_file} or {roi_csv_inner}.")
                else:
                    sorted_df = new_cum_df_inner.sort_values(by = collate_join_left, ascending = [True for x in range(len(collate_join_left))])
                    sorted_df.reset_index(drop=True,inplace=True)
                    created_datetime = get_datetimestring_utc()
                    roi_csv_inner_backup = newfile(assocfile=roi_csv_inner,suffix=f"{created_datetime}")
                    shutil.copy(roi_csv_inner,roi_csv_inner_backup)
                    sorted_df.to_csv(roi_csv_inner,sep=LSEP,header=True, index=False)

                    roi_csv_inner_json_backup = newfile(assocfile=roi_csv_inner_json,suffix=f"{created_datetime}")
                    shutil.copy(roi_csv_inner_json,roi_csv_inner_json_backup)

                    metadata = {}
                    metadata["History"]={}
                    old_metadata = {}
                    previous_metadata_file = newfile(assocfile=group_file,extension="json")
                    with open(previous_metadata_file,"r") as infile:
                        old_metadata = json.load(infile)
                    if old_metadata and "History" in old_metadata.keys():
                        if isinstance(old_metadata["History"],dict):
                            for itemkey,itemvalue in old_metadata["History"].items():
                                metadata["History"][itemkey] = itemvalue
                        else:
                            metadata["History"]["UnknownDate"] = old_metadata["History"]


                    created_datetime = get_datetimestring_utc()
                    metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
                    metadata = updateParams(metadata,"Title","collate_csv_group.py: Inner Join (both tables)")
                    metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Only matched columns are retained.")
                    metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
                    metadata = updateParams(metadata,"InputFiles",f"{roi_csv_inner_left},{roi_csv_inner_right}")
                    roi_csv_inner_json = create_metadata(roi_csv_inner, created_datetime, metadata = metadata)



            if os.path.basename(group_file) == os.path.basename(roi_csv_outer):
                new_cum_df_outer  = pd.DataFrame()
                group_df = pd.read_table(group_file,sep=LSEP)
                new_df = pd.read_table(roi_csv_outer,sep=LSEP)
                new_cum_df_outer = pd.concat([group_df,new_df],join="outer").drop_duplicates(ignore_index=True)

                if new_cum_df_outer.empty:
                    IFLOGGER.info("Problem reading files {group_file} or {roi_csv_outer}.")
                else:
                    sorted_df = new_cum_df_outer.sort_values(by = collate_join_left, ascending = [True for x in range(len(collate_join_left))])
                    sorted_df.reset_index(drop=True,inplace=True)
                    created_datetime = get_datetimestring_utc()
                    roi_csv_outer_backup = newfile(assocfile=roi_csv_outer,suffix=f"{created_datetime}")
                    shutil.copy(roi_csv_outer,roi_csv_outer_backup)
                    sorted_df.to_csv(roi_csv_outer,sep=LSEP,header=True, index=False)

                    roi_csv_outer_json_backup = newfile(assocfile=roi_csv_outer_json,suffix=f"{created_datetime}")
                    shutil.copy(roi_csv_outer_json,roi_csv_outer_json_backup)


                    metadata = {}
                    metadata["History"]={}
                    old_metadata = {}
                    previous_metadata_file = newfile(assocfile=group_file,extension="json")
                    with open(previous_metadata_file,"r") as infile:
                        old_metadata = json.load(infile)
                    if old_metadata and "History" in old_metadata.keys():
                        if isinstance(old_metadata["History"],dict):
                            for itemkey,itemvalue in old_metadata["History"].items():
                                metadata["History"][itemkey] = itemvalue
                        else:
                            metadata["History"]["UnknownDate"] = old_metadata["History"]

                    created_datetime = get_datetimestring_utc()
                    metadata["History"][created_datetime] = f"Updated with {len(participants_label)} subjects from {participants_label[0]} to {participants_label[-1]}"
                    metadata = updateParams(metadata,"Title","collate_csv_group.py: collate single table without join")
                    metadata = updateParams(metadata,"Description","Combine csv files of provided participants into group table. Unmatched columns are retained.")
                    metadata = updateParams(metadata,"Pipeline",f"{pipeline}")
                    metadata = updateParams(metadata,"InputFiles",f"{roi_csv_outer}")
                    roi_csv_outer_json = create_metadata(roi_csv_outer, created_datetime, metadata = metadata)


    out_files.insert(0,roi_csv_inner)
    out_files.insert(1,roi_csv_inner_json)
    out_files.insert(2,roi_csv_outer)
    out_files.insert(3,roi_csv_outer_json)

    return {
        "roi_csv_inner":roi_csv_inner,
        "roi_csv_inner_metadata":roi_csv_inner_json,
        "roi_csv_outer":roi_csv_outer,
        "roi_csv_outer_metadata":roi_csv_outer_json,
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
    roi_csv_inner_metadata = File(desc='metadata for CSV results file - inner join')
    roi_csv_outer = File(desc='CSV file of results')
    roi_csv_outer_metadata = File(desc='metadata for CSV results file - outer join')
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


