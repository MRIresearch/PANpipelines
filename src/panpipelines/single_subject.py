#!/usr/bin/env python
from panpipelines.utils.util_functions import *
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from functools import partial
import json
import pandas as pd
import os
import datetime
import logging
import sys
from panpipelines.version import __version__
from panpipelines import Factory

LOGGER = logger_setup("panpipelines.single_subject", logging.DEBUG)
logger_addstdout(LOGGER, logging.INFO)

panFactory = Factory.getPANFactory()

def runSingleSubject(participant_label, xnat_project, session_label, pipeline, pipeline_class, pipeline_outdir, panpipe_labels,bids_dir,cred_user,cred_password, execution_json,analysis_level="participant"):
    panpipe_labels = updateParams(panpipe_labels,"PARTICIPANT_LABEL",participant_label)
    panpipe_labels = updateParams(panpipe_labels,"PARTICIPANT_XNAT_PROJECT",xnat_project)
    panpipe_labels = updateParams(panpipe_labels,"PARTICIPANT_SESSION",session_label)

    pipeline_outdir=os.path.join(pipeline_outdir,xnat_project)
    if not os.path.exists(pipeline_outdir):
        os.makedirs(pipeline_outdir,exist_ok=True)

    participant_index = getParams(panpipe_labels,"PARTICIPANT_INDEX")
    if participant_index is None:
        participant_index = ""
    else:
        participant_index = "_" + str(participant_index)
        
    datelabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if not session_label:
        LOGFILE=os.path.join(pipeline_outdir,f"{participant_label}{participant_index}_{datelabel}_{xnat_project}_{pipeline}_single_subject.log")
    else:
        LOGFILE=os.path.join(pipeline_outdir,f"{participant_label}{participant_index}_{session_label}_{datelabel}_{xnat_project}_{pipeline}_single_subject.log")
    logger_addfile(LOGGER, LOGFILE, logging.DEBUG)
    nipype_loggers_setup(logging.INFO,LOGFILE,logging.DEBUG)

    LOGGER.info(f"Pan Processing for single subject: Running {pipeline} pipeline for {participant_label}")
    LOGGER.info(f"start logging to {LOGFILE}")

    
    getSubjectBids(panpipe_labels,bids_dir,participant_label,xnat_project,cred_user,cred_password)

    panProcessor = panFactory.get_processflow(pipeline_class)

    if not session_label:
        pipeline_outdir_subject = os.path.join(pipeline_outdir,"sub-"+participant_label)
    else:
        pipeline_outdir_subject = os.path.join(pipeline_outdir,"sub-"+participant_label,"ses-"+session_label)

    PanProc = panProcessor(panpipe_labels,pipeline_outdir_subject, participant_label, name=pipeline,LOGGER=LOGGER,execution=execution_json,analysis_level=analysis_level,participant_project=xnat_project, participant_session=session_label)
    PanProc.run()

    LOGGER.debug(f"\nDump of configuration settings for {participant_label} run of {pipeline}")
    LOGGER.debug("---------------------------------------------------------------------------------")
    LOGGER.debug(f"{panpipe_labels!r}")
    LOGGER.debug("\n------  environment dump -----------")
    LOGGER.debug(os.environ)

def parse_params():
    parser = ArgumentParser(description="Pan pipelines")
    PathExists = partial(path_exists, parser=parser)
    parser.add_argument("config_file", type=PathExists, help="Pipeline Configuration File")
    parser.add_argument("pipeline", help="single running pipeline")
    parser.add_argument("credentials", help="credential file")
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    return parser

def main():
    
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()

    print(f"Running {__file__} v{__version__}")

    panpipe_labels={}
    panpipe_labels = updateParams(panpipe_labels,'PWD',str(os.getcwd()))

    panpipeconfig_file=str(args.config_file)
    panpipeconfig_json=None
    if os.path.exists(panpipeconfig_file):
        with open(panpipeconfig_file, 'r') as infile:
            panpipeconfig_json = json.load(infile)
    panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels,uselabel=False)

    pipeline=args.pipeline

    pipeline_class = getParams(panpipe_labels,"PIPELINE_CLASS")
    if pipeline_class is None:
        pipeline_class = pipeline

    use_pipeline_desc = getParams(panpipe_labels,"USE_PIPELINE_DESC")
    if use_pipeline_desc is None:
        use_pipeline_desc = ""

    pipeline_desc = getParams(panpipe_labels,"PIPELINE_DESC")
    if pipeline_desc is None or use_pipeline_desc == "N":
        pipeline_desc = pipeline 
    else:
        pipeline_desc = "".join([x if x.isalnum() else "_" for x in pipeline_desc]) 

    pipeline_outdir=os.path.join(getParams(panpipe_labels,"PIPELINE_DIR"),pipeline_desc)
    if not os.path.exists(pipeline_outdir):
        os.makedirs(pipeline_outdir,exist_ok=True)

    lock_dir=getParams(panpipe_labels,"LOCK_DIR")
    if lock_dir:
        if not os.path.exists(lock_dir):
            os.makedirs(lock_dir,exist_ok=True)
    else:
        lock_dir=os.path.join(getParams(panpipe_labels,"PIPELINE_DIR"),"datalocks")
        if not os.path.exists(lock_dir):
            os.makedirs(lock_dir,exist_ok=True)
        panpipe_labels = updateParams(panpipe_labels,"LOCK_DIR",lock_dir)

    credentials = os.path.abspath(args.credentials)
    if os.path.exists(credentials):
        with open(credentials, 'r') as infile:
            cred_dict = json.load(infile)
            cred_user = getParams(cred_dict,"user")
            cred_password = getParams(cred_dict,"password")

    execution_json=getParams(panpipe_labels,"NIPYPE_CONFIG")
    if execution_json is None:
        execution_json = {} 


    participants_file = getParams(panpipe_labels,"PARTICIPANTS_FILE")
    sessions_file = getParams(panpipe_labels,"SESSIONS_FILE")
    bids_dir = getParams(panpipe_labels,"BIDS_DIR")

    # if participant label not provided then infer as submitted job
    ARRAY_INDEX = getParams(panpipe_labels,"ARRAY_INDEX")
    if ARRAY_INDEX is not None and ARRAY_INDEX in os.environ.keys():
        participant_index = int(os.environ[ARRAY_INDEX])
        panpipe_labels = updateParams(panpipe_labels, "PARTICIPANT_INDEX",str(participant_index))
        if not sessions_file:
            df = pd.read_table(participants_file)
        else:
            df = pd.read_table(sessions_file)
        if participant_index <= len(df):
            participant_label = drop_sub(df['bids_participant_id'].iloc[participant_index - 1])
            xnat_project = df['project'].iloc[participant_index - 1]
            if sessions_file:
                session_label = drop_ses(df['bids_session_id'].iloc[participant_index - 1])
            else:
                session_label=None
            runSingleSubject(participant_label,xnat_project,session_label, pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json,analysis_level="participant")


        else:
            print("Problem: ARRAY_INDEX {} greater than length of participants file {}".format(participant_index,participants_file))
    else:
        print("{} used as ARRAY_INDEX but not defined in os.environs".format(ARRAY_INDEX))


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()