import pandas as pd 
import sys
import os
import json
from collections import OrderedDict
import glob
import datetime
import time
from datetime import timedelta
import logging
import re

start_time = time.time()

LOGGER = logging.getLogger("validate_panpipelines")
LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
loglevel = logging.INFO
stdout_handler.setLevel(loglevel)
stdout_handler.setFormatter(formatter)
LOGGER.addHandler(stdout_handler)

cwd = os.getcwd()
proc_dir = cwd

args = sys.argv
if len(args) > 1:
    output_dir = args[1]
    if len(args) > 2:
        pan_config = f"{proc_dir}/config/{args[2]}"
        if len(args) > 3:
            bids_dir = args[3]
        else:
            bids_dir = f"./ALLPAN_Data/BIDS"
    else:
        pan_config = f"{proc_dir}/config/pan.config"
else:
    output_dir = "PAN_processing_outputs"

run_name = os.path.basename(pan_config).replace(".","_")

with open(pan_config,"r") as infile:
    pan_config_json = json.load(infile)
pan_config_pipeline_list = list(pan_config_json.keys())
EXCLUDE=["ftp","dummy","all_","pandb"]
PIPELINE_LIST_ORIG = [item for i,item in enumerate(pan_config_pipeline_list) if not any(keyword in item for keyword in EXCLUDE)]

DATESTAMP=datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

project="*"

wf_ref="{proc_dir}/{output_dir}/{pipeline}/{project}/{sub}/{ses}/{pipeline}_wf"
group_wf_ref="{proc_dir}/{output_dir}/{pipeline}/group/{pipeline}_wf"

# override
PIPELINE_LIST = []

PIPELINES=OrderedDict()

PIPELINES["basil_voxel_mansdc"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/basil_node/basiloutput/native_space/pvcorr/perfusion_wm_var_calib.nii.gz",
    "action": "present^^^"
}

PIPELINES["basil_voxel_nodc"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/basil_node/basiloutput/native_space/pvcorr/perfusion_wm_var_calib.nii.gz",
    "action": "present^^^"
}

PIPELINES["basil_htmlreport"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/reports_node/html_report/*.html",
    "action": "present^^^"
}

PIPELINES["basil_nodc_htmlreport"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/reports_node/html_report/*.html",
    "action": "present^^^"
}

PIPELINES["freesurfer"]= {
    "ref" : wf_ref,
    "file" : wf_ref + "/freesurfer_node/subjects_dir/{sub}/scripts/recon-all.log",
    "action": "grep^^^finished without error"
}

PIPELINES["preproc"] = {
    "ref" : wf_ref,
    "file":"{proc_dir}/{output_dir}/derivatives/{pipeline}/{sub}/{ses}/{sub}_{ses}_asl_chemical_shift_artefact.nii.gz",
    "action": "present^^^"
}

PIPELINES["preproc_nodc"] = {
    "ref" : wf_ref,
    "file":"{proc_dir}/{output_dir}/derivatives/{pipeline}/{sub}/{ses}/{sub}_{ses}_asl_chemical_shift_artefact.nii.gz",
    "action": "present^^^"
}

PIPELINES["mriqc"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/mriqc_node/mriqcout/*.html",
    "action": "present^^^"
}

PIPELINES["aslprep_qc"] = {
    "ref" : wf_ref,
    "file" : wf_ref + "/aslprep_node/aslprep/{sub}/{ses}/perf/{sub}_{ses}_*desc-preproc_asl.nii.gz",
    "action": "present^^^"
}


PIPELINES["xnat_mri_sessions"]= {
    "ref" : group_wf_ref,
    "file" : "{output_dir}/derivatives/output_tables/{pipeline}/*.csv",
    "action": "present^^^"
}


PIPELINES["fmriprep_v2411"] = {
    "ref" : wf_ref,
    "file" : wf_ref + "/fmriprep_node/fmrioutput/{sub}/{ses}/func/{sub}_{ses}_*desc-preproc_bold.nii.gz",
    "action": "present^^^"
}

PIPELINES["qsiprep_v0214"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/qsiprep_node/qsiprep/{sub}/{ses}/dwi/{sub}_{ses}_space-T1w_desc-preproc_dwi.nii.gz",
    "action": "present^^^"
}

PIPELINES["qsiprep_v101"]= {
    "ref" : wf_ref,
    "file": wf_ref + "/qsiprep_node/qsiprep_out/{sub}/{ses}/dwi/{sub}_{ses}_space-ACPC_desc-preproc_dwi.nii.gz",
    "action": "present^^^"
}

PIPELINES["qsiprep_v0214_affine_transform"]= {
    "ref" : wf_ref,
    "file" : wf_ref + "/*GenericAffine.mat",
    "action": "present^^^"
}

PIPELINES["noddi_v0214"] = {
    "ref" : wf_ref,
    "file" : wf_ref + "/noddi_node/qsirecon/{sub}/{ses}/dwi/{sub}_{ses}_space-T1w_desc-preproc_desc-ICVF_NODDI.nii.gz",
    "action": "present^^^"
}

PIPELINES["tensor_v0214"] = {
    "ref" : wf_ref,
    "file" : wf_ref + "/tensor_node/tensor_metrics/{sub}_{ses}_space-T1w_desc-preproc_desc-fa.nii.gz",
    "action": "present^^^"
}

# APPEND 
for pipeline in PIPELINE_LIST_ORIG:

    if pipeline not in PIPELINE_LIST:
        PIPELINE_LIST.append(pipeline)


    if pipeline not in PIPELINES.keys():
        
        pipeline_class = ""
        if pipeline in pan_config_json.keys():
            if "PIPELINE_CLASS" in pan_config_json[pipeline].keys():
                pipeline_class = pan_config_json[pipeline]["PIPELINE_CLASS"]


        ref = wf_ref
        file = wf_ref + "/subject_metrics_map/mapflow/_subject_metrics_map0/{sub}_{ses}_roi_output_dir/*.csv"
        action = "present^^^"

        if "roiextract_panpipeline" in pipeline_class:
            file = wf_ref + "/subject_metrics_map/mapflow/_subject_metrics_map0/{sub}_{ses}_roi_output_dir/*.csv"
            
        elif "textmeasures_panpipeline" in pipeline_class:
            file = wf_ref + "/subject_text_map/mapflow/_subject_text_map0/*_roi_output_dir/*.csv"
            action = "present^^^"
        elif "collatesubject" in pipeline or "collatecsv_panpipeline" in pipeline_class:
            file = wf_ref + "/collate_csv_single_node/*_roi_output_dir/*.csv"
        elif "collategroup" in pipeline or "collatecsvgroup_panpipeline" in pipeline_class:
            ref = group_wf_ref
            file =  "{output_dir}/derivatives/output_tables/{pipeline}/*.csv"
        elif pipeline.startswith("freewater"):
            file = wf_ref + "/freewater_node/freewater/*fraction.nii.gz"
        elif pipeline == "tractseg":
            file = wf_ref + "/tractseg_node/tractseg_out/bundles_segmentations_native_bin/CC.nii.gz"
        elif pipeline.startswith("freesurferextra_direct"):
            file  =  wf_ref + "/freesurferextra_node/*completed*"
            action = "grep^^^computing statistics for each annotation in lobes.annot"
        elif pipeline.startswith("xcpd"):
            file = wf_ref + "/xcpd_node/xcp_out/{sub}/{ses}/func/*relmat.tsv"
        elif pipeline.startswith("mriqcgroup"):
            ref = group_wf_ref
            file =  "{output_dir}/derivatives/output_tables/{pipeline}/{pipeline}out/*.json"
        elif pipeline.startswith("amiconoddi_"):
            ref = wf_ref
            file = wf_ref + "/pancontainergroup_node/amico_output/fit_FWF.nii.gz"
        elif pipeline.startswith("postxcpd"):
            ref = wf_ref
            file = wf_ref + "/postxcpd_node/*outdir/*.csv"
        elif "transform_panpipeline" in pipeline_class:
            ref = wf_ref
            file = wf_ref + "/subject_transform_map/mapflow/_subject_transform_map0/{sub}_{ses}*.nii.gz"
        elif "registration_panpipeline" in pipeline_class:
            ref = wf_ref
            file = wf_ref + "/subject_register/{sub}_{ses}*.mat"
        elif "harmonize" in pipeline:
            ref = group_wf_ref
            file = group_wf_ref + "/*.csv"
        elif "lstai" in pipeline:
            ref = wf_ref
            file = wf_ref + "/results/*.csv"
        elif "update_wmh_measures" in pipeline:
            ref = group_wf_ref
            file = group_wf_ref + "/*.csv"

        
        PIPELINES[pipeline] = {
            "ref" : ref,
            "file" : file,
            "action": action
        }

HMLID = "hml_id"
PROJECT="project"
SUBID = "subject_id"
SESID = "session_id"
BIDS_PARTICIPANT_ID = "bids_participant_id"
BIDS_SESSION_ID = "bids_session_id"
XNAT_SUBJECT_LABEL = "xnat_subject_label"
XNAT_SESSION_LABEL = "xnat_session_label"
INDEX = "index"

table_header = {}
table_header[HMLID]=""
table_header[PROJECT]=""
table_header[SUBID] = ""
table_header[SESID] = ""
for pipeline in PIPELINE_LIST:
    table_header[pipeline]=""

def export_labels(panpipe_labels,export_file):
    with open(export_file,"w") as outfile:
        json.dump(panpipe_labels,outfile,indent=1)

def initializeRow(table_dict):
    tablerow = OrderedDict()
    for column in table_dict:
        tablerow[column]=""
    return tablerow

def appendTableRows(subject_row,table_data):
    if subject_row and isinstance(subject_row,dict):
        subject_row = [subject_row]
    elif not subject_row:
        subject_row = []


    for table_row in subject_row:
        new_table_row = []
        for itemkey, itemvalue in table_row.items():
            new_table_row.append(str(itemvalue))
        table_data.append(new_table_row)
    return table_data

def loadParams(pardict, key, value, update=True):
    if key and value:
        if key in pardict:
            if not pardict[key] or update:
                pardict[key]=value
        else:
            pardict[key]=value
    return pardict

def successful_run(file,action):
    action_items = action.split("^^^")
    if action_items[0] == "present":
        if len(glob.glob(file)) > 0:
            return True
    elif action_items[0] == "grep":
        if len(action_items)>1 and len(glob.glob(file)) > 0:
            target_file = glob.glob(file)[0]
            target_string = action_items[1]
            try:
                with open(target_file,"r") as infile:
                    lines = infile.readlines()
                find_list = [x for x in lines if target_string in x]
                if len(find_list) > 0:
                    return True
            except FileNotFoundError:
                pass

    return False

bids_table_data = []
bids_data_dict={}
bids_data_dict[BIDS_PARTICIPANT_ID] = ""
bids_data_dict[BIDS_SESSION_ID] = ""
bids_data_dict[XNAT_SUBJECT_LABEL] = ""
bids_data_dict[HMLID] = ""
for dirs in glob.glob(bids_dir + "/*/ses*"):
    bids_ses = dirs.split("/")[-1]
    bids_sub = dirs.split("/")[-2]
    bids_hmlid = bids_sub.split("-")[1]
    bids_subject_row = initializeRow(bids_data_dict)
    bids_subject_row[BIDS_PARTICIPANT_ID] = bids_sub 
    bids_subject_row[BIDS_SESSION_ID] = bids_ses
    bids_subject_row[XNAT_SUBJECT_LABEL] = bids_hmlid
    bids_subject_row[HMLID] = bids_hmlid

    bids_table_data = appendTableRows(bids_subject_row, bids_table_data)

if bids_table_data:
    bids_table_columns=list(bids_subject_row.keys())
    bids_df = pd.DataFrame(bids_table_data,columns=bids_table_columns)

df = bids_df

table_data = []
table_columns = df.columns.tolist()

for dfnum in range(len(df)):
    df_table_columns=list(df.keys())
    subject_row=initializeRow(table_header)

    sub = df.iloc[dfnum].bids_participant_id
    xnat_sub = df.iloc[dfnum].xnat_subject_label
    ses = df.iloc[dfnum].bids_session_id

    if "xnat_session_label" in table_columns:
        xnat_ses = df.iloc[dfnum].xnat_session_label
    else:
        xnat_ses = ses


    if PROJECT in table_columns:
        project = df.iloc[dfnum][PROJECT]
        loadParams(subject_row,PROJECT,project)
    else:
        loadParams(subject_row, PROJECT, "PAN_October_2025")

    if HMLID in table_columns:
        hml_id = df.iloc[dfnum][HMLID]
        loadParams(subject_row,HMLID,hml_id)
    else:
        if not pd.isna(sub):
            hml_id=sub.split("sub-")[1]
            loadParams(subject_row,HMLID,hml_id)
        else:
            hml_id=xnat_sub
            loadParams(subject_row,HMLID,hml_id)

    if not pd.isna(sub):
        loadParams(subject_row,SUBID,sub)
    else:
        loadParams(subject_row,SUBID,"sub-"+hml_id)

    
    if not pd.isna(ses):
        loadParams(subject_row,SESID,ses)
    else:
        if xnat_ses:
            SES_ZFILL=2
            session_parts = xnat_ses.split("_")
            if session_parts:
                session_num_string = session_parts[-1]
                num_find = re.findall(r'\d+',session_num_string)
                if len(num_find) > 0:
                    session_int = int(num_find[0])
                    ses = str(session_int).zfill(SES_ZFILL)
                else:
                    ses="2".zfill(SES_ZFILL)
        else:
            ses="2".zfill(SES_ZFILL)
        loadParams(subject_row,SESID,"ses-"+ses)
    
    for pipeline in PIPELINE_LIST:

        if "file" in PIPELINES[pipeline].keys():

            if not pd.isna(sub) and not pd.isna(ses):
                search_df = bids_df[(bids_df[BIDS_PARTICIPANT_ID]==sub) & (bids_df[BIDS_SESSION_ID]==ses)]
                if not search_df.empty:
                    started = PIPELINES[pipeline]["ref"].replace("{proc_dir}",proc_dir).replace("{output_dir}",output_dir).replace("{project}",project).replace("{pipeline}",pipeline).replace("{sub}",sub).replace("{ses}",ses)
                    started_dir = glob.glob(started)
                    if started_dir and os.path.exists(started_dir[0]):
                        proc_file = PIPELINES[pipeline]["file"].replace("{proc_dir}",proc_dir).replace("{output_dir}",output_dir).replace("{project}",project).replace("{pipeline}",pipeline).replace("{sub}",sub).replace("{ses}",ses)
                        action = PIPELINES[pipeline]["action"]

                        if not successful_run(proc_file, action):
                            loadParams(subject_row,pipeline,"failed")
                        else:
                            loadParams(subject_row,pipeline,"complete")
                    else:
                        loadParams(subject_row,pipeline,"not started")
                else:
                    loadParams(subject_row,pipeline,"bids_missing")
            else:
                loadParams(subject_row,pipeline,"xnat_missing")

        else:
            loadParams(subject_row,pipeline,"N/A")

    table_data = appendTableRows(subject_row, table_data)

if table_data:
    validate_out=os.path.join(f"{proc_dir}",f"validate_{DATESTAMP}_{run_name}.csv")
    table_columns = list(table_header.keys())
    validate_df = pd.DataFrame(table_data,columns=table_columns)
    sorted_df = validate_df.sort_values(by=[HMLID,"session_id"], ascending=[True,True])
    sorted_df.reset_index(drop=True,inplace=True)
    sorted_df.to_csv(validate_out,sep=",",index=False)
    print(f"{validate_out} created")

time_elapsed = time.time() - start_time
time_delta = str(timedelta(seconds=time_elapsed))
LOGGER.info(f"Elapsed Time : {time_elapsed} seconds")
LOGGER.info(f"Elapsed Time : {time_delta}") 
    