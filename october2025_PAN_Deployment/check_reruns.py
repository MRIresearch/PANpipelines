import pandas as pd
import glob
import datetime
import os
from panpipelines.utils.util_functions import *

cwd = os.getcwd()
proc_dir = cwd
args = sys.argv
if len(args) > 1:
    validate_csv = args[1]
    if len(args) > 2:
        pan_config = f"{proc_dir}/config/{args[2]}"
        if len(args) > 3:
            bids_dir = args[3]
        else:
            bids_dir = f"./ALLPAN_Data/BIDS"
    else:
        pan_config = f"{proc_dir}/config/pan.config"
else:
    validate_csv="validate_results_2025-12-18-10-14-33.csv"

run_name = os.path.basename(pan_config).replace(".","_")


def iterate_incompletes(orig_incomplete_columns,incomplete_columns,iterate_list=[]):
    overlap_dict={}

    if not orig_incomplete_columns:
        return iterate_list

    for incomp in orig_incomplete_columns:
        dependents = get_dependent_pipelines(pan_config_json,[incomp],ALL_PIPELINES)
        overlaps = list(set(incomplete_columns) & set(dependents))
        overlap_nums = len(overlaps)
        overlap_dict[incomp] = {}
        overlap_dict[incomp]["nums"] = overlap_nums
        overlap_dict[incomp]["overlaps"] = overlaps

    if overlap_dict and len(overlap_dict.keys()) > 0:
        max_pipe = max(overlap_dict, key=lambda k: overlap_dict[k]["nums"])
        max_pipedict = overlap_dict[max_pipe]
        max_overlaps = max_pipedict['overlaps']
        max_value = max_pipedict['nums']
        iterate_list.append(max_pipe)
        next_incomplete_columns = list(set(incomplete_columns) - set(max_overlaps))
        next_orig_columns = list(set(orig_incomplete_columns) - set(max_overlaps))
        iterate_incompletes(next_orig_columns,next_incomplete_columns,iterate_list)

    return iterate_list



valpath=glob.glob(validate_csv)[0]
df =pd.read_table(valpath,sep=",")

with open(pan_config,"r") as infile:
    pan_config_json = json.load(infile)
pan_config_pipeline_list = list(pan_config_json.keys())
EXCLUDE=["ftp","dummy","all_","pandb"]
ALL_PIPELINES = [item for i,item in enumerate(pan_config_pipeline_list) if not any(keyword in item for keyword in EXCLUDE)]

ID_COLS=['hml_id', 'project', 'subject_id', 'session_id']
NOT_FOLLOW_EXCLUDE=['basilmeasures_multipld_gmhemi_tissue_native_pvcorr_maskchem']

search_df = df
#search_df = df[df["hml_id"].isin(["HML0791","HML0804","HML0829","HML0850","HML0856","HML0873","HML0878","HML0909","HML0916","HML0920","HML0922","HML0930","HML0935","HML0940","HML0942"])]
#if search_df.empty:
#    search_df = df

# Iterate through each row
table_columns=["subject_id","session_id"]
table_columns_raw = ["subject_id","session_id"]
table_data=[]
table_data_raw = []
tidx=-1
for idx, row in search_df.iterrows():
    tidx=tidx+1
    table_row=["" for x in table_columns]
    table_row_raw=["" for x in table_columns_raw]
    hmlid = df.iloc[idx].hml_id
    subject_id = df.iloc[idx].subject_id
    session_id = df.iloc[idx].session_id
    table_row[0]=subject_id
    table_row[1]=session_id
    table_row_raw[0]=subject_id
    table_row_raw[1]=session_id
    incomplete_columns = row[row != 'complete'].index.tolist()
    incomplete_columns = [c for c in incomplete_columns if c not in ID_COLS]

    if 'follow' not in session_id:
        incomplete_columns = [c for c in incomplete_columns if c not in NOT_FOLLOW_EXCLUDE]

    # obtain full dependency list
    orig_incomplete_columns = incomplete_columns.copy()
    #print(f"Row {idx} - {hmlid}, {subject_id}, {session_id} - original incomplete columns: {orig_incomplete_columns}")

    for incomp in incomplete_columns:
        incomplete_columns.extend(get_dependent_pipelines(pan_config_json,[incomp],ALL_PIPELINES))
        incomplete_columns=list(set(incomplete_columns))
    
    #print(f"Row {idx} - {hmlid}, {subject_id}, {session_id} - Incomplete columns: {incomplete_columns}")
    runlist = iterate_incompletes(orig_incomplete_columns,incomplete_columns,iterate_list=[])
    print(f"Run {hmlid}, {subject_id}, {session_id} = {runlist}")

    for run_pipe in runlist:
        if run_pipe in table_columns:
            run_pipe_posn = table_columns.index(run_pipe)
            table_row[run_pipe_posn] = "rerun"
        else:
            table_columns.append(run_pipe)
            table_row.append("rerun")
            if tidx > 0:
                for rev in range(tidx):
                    table_data[rev].append("")

    table_data.append(table_row)

    for raw_pipe in orig_incomplete_columns:
        if raw_pipe in table_columns_raw:
            raw_pipe_posn = table_columns_raw.index(raw_pipe)
            table_row_raw[raw_pipe_posn] = "fail"
        else:
            table_columns_raw.append(raw_pipe)
            table_row_raw.append("fail")
            if tidx > 0:
                for rev in range(tidx):
                    table_data_raw[rev].append("")

    table_data_raw.append(table_row_raw)


if table_data and table_columns:
    df = pd.DataFrame(table_data,columns = table_columns)
    df.to_csv(f"rerun_table_{run_name}.csv",sep=",",index=False)
    pipeline_cols = df.columns[2:]
    filtered_df = df[(df[pipeline_cols].notna() & (df[pipeline_cols] != "")).any(axis=1)]
    filtered_df.to_csv(f"rerun_table_filtered_{run_name}.csv",sep=",",index=False)

if table_data_raw and table_columns_raw:
    df = pd.DataFrame(table_data_raw,columns = table_columns_raw)
    df.to_csv(f"rerun_table_raw_{run_name}.csv",sep=",",index=False)
    pipeline_cols = df.columns[2:]
    filtered_df = df[(df[pipeline_cols].notna() & (df[pipeline_cols] != "")).any(axis=1)]
    filtered_df.to_csv(f"rerun_table_raw_filtered_{run_name}.csv",sep=",",index=False)
