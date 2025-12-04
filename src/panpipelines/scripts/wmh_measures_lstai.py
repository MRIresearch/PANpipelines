import pandas as pd
import json
import argparse
import os
from pathlib import Path
from panpipelines.utils.util_functions import *
from collections import OrderedDict


site_dict = {
    "001_HML" : "Tucson",
    "002_HML" : "Miami",
    "003_HML" : "Atlanta",
    "004_HML" : "Baltimore"    
}

def appendTableRows(table_rows,table_data):    
    for table_row in table_rows:
        new_table_row = []
        for itemkey, itemvalue in table_row.items():
            new_table_row.append(str(itemvalue))
        table_data.append(new_table_row)
    return table_data

def initializeRow():
    tablerow = OrderedDict()
    for column in table_header:
        tablerow[column]=""
    return tablerow

def loadParams(pardict, key, value, update=True):
    if key:
        if key in pardict:
            if not pardict[key] or update:
                pardict[key]=value
    return pardict

# Set up argument parser
def parse_params():
    parser = argparse.ArgumentParser(description="Parse through all LSTAI results to create more accessible CSV file.")
    parser.add_argument('--output', default='results.csv', help="The name of the output CSV file (default: results.csv).")
    parser.add_argument('--input_dir',  help="The input directory for each subject.")
    parser.add_argument("--pipeline_config_file", type=Path, help="Pipeline Config File")
    parser.add_argument("--participants_label",nargs='*',help="list of participants")
    parser.add_argument("--participants_project",nargs='*',help="list of projects")
    parser.add_argument("--participants_sessions",nargs='*',help="list of sessions")
    return parser

if __name__ == "__main__":

    parser=parse_params()
    args, unknown_args = parser.parse_known_args()

    output = args.output
    input_dir = args.input_dir

    pipeline_config_file = None
    if args.pipeline_config_file:
        if Path(args.pipeline_config_file).exists():
            pipeline_config_file = str(args.pipeline_config_file)

    labels_dict={}
    if pipeline_config_file:
        panpipeconfig_file=str(pipeline_config_file)
        if os.path.exists(pipeline_config_file):
           print(f"{pipeline_config_file} exists.")
           with open(pipeline_config_file,'r') as infile:
               labels_dict = json.load(infile)
    
    
    if labels_dict:
        cwd = getParams(labels_dict,"CWD")
        participants_label = getParams(labels_dict,'GROUP_PARTICIPANTS_LABEL')
        participants_project = getParams(labels_dict,'GROUP_PARTICIPANTS_XNAT_PROJECT')
        participants_session = getParams(labels_dict,'GROUP_SESSION_LABEL')
        ADD_CUMULATIVE = isTrue(getParams(labels_dict,"ADD_CUMULATIVE"))
        LAST_OUTPUT_FILES = getParams(labels_dict,"LAST_OUTPUT_FILES")
        participant_exclusions = getParams(labels_dict,"EXCLUDED_PARTICIPANTS")
        if participant_exclusions:
            subject_exclusions = process_exclusions(participant_exclusions)
        collate_join_left= getParams(labels_dict,"COLLATECOLS_JOIN_LEFT")
        if not collate_join_left:
            collate_join_left=["subject_id","session_id"]
            
    else:
        cwd = os.path.dirname(tempfile.mkstemp()[1])
        participants_label = args.participants_label
        participants_project = args.participants_project
        participants_session = args.participants_session
        ADD_CUMULATIVE=False
        LAST_OUTPUT_FILES=None
        participant_exclusions = None
        subject_exclusions = []
        collate_join_left=["subject_id","session_id"]

    if not os.path.dirname(output):
        output = os.path.join(cwd,output)

    table_header = []
    table_header.append("hml_id")
    table_header.append("subject_id")
    table_header.append("session_id")
    table_header.append("site")
    table_header.append("site_id")
    table_header.append("wmh_num_all")
    table_header.append("wmh_num_vox_all")
    table_header.append("wmh_volume_all")

    table_data = []

    regions = ["Periventricular", "Juxtacortical", "Subcortical", "Infratentorial"]
    for reg in regions:
        table_header.append(f"wmh_num_{reg.lower()}")
        table_header.append(f"wmh_num_vox_{reg.lower()}")
        table_header.append(f"wmh_volume_{reg.lower()}")

    for part_vals in zip(participants_label,participants_project,participants_session):
        table_row = initializeRow()
        hml_id = part_vals[0]
        site_id = part_vals[1]
        session_label = part_vals[2]
        subject_id = f"sub-{hml_id}"
        session_id = f"ses-{session_label}"

        loadParams(table_row,"hml_id",hml_id)
        loadParams(table_row,"subject_id",subject_id)
        loadParams(table_row,"session_id",session_id)
        loadParams(table_row,"site",site_dict[site_id])
        loadParams(table_row,"site_id",site_id)

        labels_dict = updateParams(labels_dict,"PARTICIPANT_LABEL",hml_id)
        labels_dict = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT",site_id)
        labels_dict = updateParams(labels_dict,"PARTICIPANT_SESSION",session_label)
        lstai_input_dir = substitute_labels(input_dir,labels_dict)
        
        total = os.path.join(lstai_input_dir,"lesion_stats.csv")
        annotated = os.path.join(lstai_input_dir,"annotated_lesion_stats.csv")
        if not os.path.exists(total) or not os.path.exists(annotated):
            print(f"{subject_id} and {session_id} LSTAI results not found")
            continue

        total_df = pd.read_table(total,sep=",")
        Num_Lesions = total_df.iloc[0].Num_Lesions
        Num_Vox = total_df.iloc[0].Num_Vox
        Lesion_Volume = total_df.iloc[0].Lesion_Volume
        Lesion_Volume = round(Lesion_Volume,2)
        loadParams(table_row,"wmh_num_all",round(Num_Lesions,2))
        loadParams(table_row,"wmh_num_vox_all",round(Num_Vox,2))
        loadParams(table_row,"wmh_volume_all",Lesion_Volume)
                
        annotated_df = pd.read_table(annotated,sep=",")
        for reg in regions:
            Num_Lesions = annotated_df.loc[annotated_df["Region"]== reg, "Num_Lesions"].values[0]
            Num_Vox = annotated_df.loc[annotated_df["Region"]== reg, "Num_Vox"].values[0]
            Lesion_Volume = annotated_df.loc[annotated_df["Region"]== reg, "Lesion_Volume"].values[0]
            Lesion_Volume = round(Lesion_Volume,2)
            loadParams(table_row,f"wmh_num_{reg.lower()}",round(Num_Lesions,2))
            loadParams(table_row,f"wmh_num_vox_{reg.lower()}",round(Num_Vox,2))
            loadParams(table_row,f"wmh_volume_{reg.lower()}",Lesion_Volume)

        table_data = appendTableRows([table_row], table_data)

    if table_data:
        result = pd.DataFrame(table_data, columns=table_header)
    else:
        result = pd.DataFrame()

    if ADD_CUMULATIVE and LAST_OUTPUT_FILES and not result.empty:
        prev_result = pd.read_table(LAST_OUTPUT_FILES,sep=",")
        new_rows = result.merge(prev_result[collate_join_left], on=collate_join_left, how="left", indicator=True)
        new_rows = new_rows[new_rows["_merge"] == "left_only"].drop(columns="_merge")

        new_result = pd.DataFrame()
        new_result = pd.concat([prev_result, new_rows], ignore_index=True)

        # mask excluded subjects at the very end
        result = mask_excludedrows(new_result, subject_exclusions, collate_join_left)


    # Save the DataFrame to a CSV file
    if not result.empty:
        result = result.sort_values(by=["subject_id","session_id"])
        result.reset_index(drop=True, inplace=True)
        result.to_csv(output, index=False)
        print(f"Data has been successfully exported to {output}.")
        output_metadata = create_metadata(output,None, metadata = {"Script":"wmh_measures_lstai.py","Description":f"collate LSTAI measures for all participants"})
    else:
        output=None
        output_metadata=None
        print(f"Problem obtaining wmh measures")

    if labels_dict:
        labels_dict["METADATA_FILE"]=output_metadata 
        labels_dict["OUTPUT_FILE"]=output
        export_labels(labels_dict,pipeline_config_file)
