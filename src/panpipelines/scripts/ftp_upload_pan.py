from urllib.parse import urlparse
from panpipelines.utils.util_functions import *
from panpipelines.utils.upload_functions import *
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from functools import partial
import json
import os
import tempfile
import glob
import multiprocessing as mp
import pandas as pd
import shutil


def parse_params():
    parser = ArgumentParser(description="Pan pipelines")
    PathExists = partial(path_exists, parser=parser)
    parser.add_argument("--ftpcredentials", help="sftp connection string")
    parser.add_argument("--urlstring", help="sftp connection string")
    parser.add_argument("--bids_dir", type=PathExists, help="bids directory")
    parser.add_argument("--participants_file", type=PathExists, help="participants_file in tsv format")
    parser.add_argument("--participant_label", nargs="*", type=drop_sub, help="filter by subject label (the sub- prefix can be removed).")
    parser.add_argument("--all_bids",default="False")
    parser.add_argument("--replace",default="True")
    parser.add_argument("--debug",default="False")
    parser.add_argument("--num_procs",type=int,default=5)
    parser.add_argument("--ftp_raw_path", help="participants_file in tsv format",default="/shared/PAN/PAN-Data/Core-E/Raw")
    parser.add_argument("--ftp_processed_path", help="participants_file in tsv format",default="/shared/PAN/PAN-Data/Core-E/Processed")
    parser.add_argument("--pipeline_config_file", type=Path, help="Pipeline Config File")

    return parser

if __name__ == "__main__":

    parser=parse_params()
    args, unknown_args = parser.parse_known_args()

    raw_path = args.ftp_raw_path
    processed_path = args.ftp_processed_path

    urlstring = args.urlstring
    if urlstring:
        parsed_url = urlparse(urlstring)
        hostname=parsed_url.hostname
        username=parsed_url.username
        password=parsed_url.password
        port=parsed_url.port
        if not port:
            port = 22

    ftpcredentials = args.ftpcredentials
    if ftpcredentials:
        with open(ftpcredentials,"r") as infile:
            ftpcred = json.load(infile)
            hostname=ftpcred["hostname"]
            username=ftpcred["username"]
            password=ftpcred["password"]
            if "port" in ftpcred.keys():
                port=int(ftpcred["password"])
            else:
                port = 22

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

    participant_label = args.participant_label
    bids_dir = str(args.bids_dir)
    if args.participants_file:
        participants_file = str(args.participants_file)
    else:
        participants_file = None

    ALLBIDS=isTrue(args.all_bids)
    REPLACE=isTrue(args.replace)
    DEBUG=isTrue(args.debug)
    PROCS=args.num_procs

    subject_list = glob.glob(os.path.join(bids_dir,"sub-*"))
    subject_list.sort()
    if ALLBIDS:
        participant_label = None
        participants_file = None
        print("ALLBIDS selected. Ignoring participants labels and participants file")

    folder = os.path.basename(bids_dir)
    if participants_file:
        df = pd.read_table(participants_file,sep="\t")
        participants_file_labels = df["hml_id"].tolist()
        subject_dir_list  = [x for x in subject_list if drop_sub(os.path.basename(x)) in participants_file_labels]
    elif participant_label:
        subject_dir_list  = [x for x in subject_list if drop_sub(os.path.basename(x)) in participant_label]
    else:
        subject_dir_list  = [x for x in subject_list]

    subject_dir_list.sort()
    remote_path_list  = [os.path.join(raw_path,folder,os.path.basename(x)) for x in subject_dir_list]

    multiproc_zip = zip(subject_dir_list,remote_path_list)
    if not DEBUG:
        par_upload_subbids=partial(ftp_upload_subjectbids, hostname=hostname,username=username,password=password,port=port,replace=REPLACE)
        with mp.Pool(PROCS) as pool:
            completedlist = pool.starmap(par_upload_subbids,multiproc_zip)
            pool.close()
            pool.join()
    else:
        for i,(source_path,remote_path) in enumerate(multiproc_zip):
            ftp_upload_subjectbids(source_path,remote_path,hostname=hostname,username=username,password=password,port=port,replace=REPLACE)


    remote_path = os.path.join(raw_path,folder)
    local_participantsTSV = os.path.join(bids_dir,"participants.tsv")
    remote_participantsTSV=os.path.join(remote_path,"participants.tsv")
    ftp_upload(local_participantsTSV ,remote_participantsTSV,hostname,username,password,port)

    local_datasetDescription = os.path.join(bids_dir,"dataset_description.json")
    remote_datasetDescription = os.path.join(remote_path,"dataset_description.json")
    ftp_upload(local_datasetDescription ,remote_datasetDescription,hostname,username,password,port)

    if labels_dict:
        cwd = getParams(labels_dict,"CWD")
    else:
        cwd = os.path.dirname(tempfile.mkstemp()[1])
    metadata_init={}
    remote_metadata_file = newfile(assocfile=os.path.dirname(remote_participantsTSV),suffix="upload-metadata",extension="json")
    local_metadata_file = newfile(outputdir=cwd,assocfile=remote_metadata_file,extension="json")

    history={}
    history["SourceBIDS"]=f"{bids_dir}"
    history["TargetBIDS"]=f"{remote_path}"

    if ALLBIDS:
        history["Description"]=f"All bids files uploaded from {bids_dir}. {len(subject_list)} participants uploaded from {os.path.basename(subject_list[0])} to {os.path.basename(subject_list[-1])}"
    else:
        if participants_file:
            participant_source = participants_file
        else:
            participant_source = participant_label
        history["Description"] =f"Incremental upload from {bids_dir} using {participant_source}. {len(subject_dir_list)} participants uploaded from {os.path.basename(subject_dir_list[0])} to {os.path.basename(subject_dir_list[-1])}"


    upload_metadata(local_metadata_file,remote_metadata_file,local_participantsTSV,remote_participantsTSV,metadata=metadata_init,history=history,hostname=hostname,username=username,password=password, port=port)


    if labels_dict:
        labels_dict["METADATA_FILE"]=local_metadata_file
        labels_dict["OUTPUT_FILE"]=local_participantsTSV
        export_labels(labels_dict,pipeline_config_file)







