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

LOGGER = logger_setup("panpipelines.group_subjects", logging.DEBUG)
logger_addstdout(LOGGER, logging.INFO)

panFactory = Factory.getPANFactory()

def runGroupSubjects(participant_label, xnat_projects, xnat_shared_projects, session_label, pipeline, pipeline_class, pipeline_outdir, panpipe_labels,bids_dir,cred_user,cred_password, execution_json,analysis_level="group",panlabel=None):

    pipeline_start = datetime.datetime.now()
    # get parent directory
    if not panlabel:
        panlabel=os.path.basename(os.path.dirname(pipeline_outdir))

    pipeline_outdir=os.path.join(pipeline_outdir,"group")
    if not os.path.exists(pipeline_outdir):
        os.makedirs(pipeline_outdir,exist_ok=True)
    
    LOGFILE=os.path.join(pipeline_outdir,f"group_{pipeline}_{panlabel}.log")
    logger_addfile(LOGGER, LOGFILE, logging.DEBUG)
    nipype_loggers_setup(logging.INFO,LOGFILE,logging.DEBUG)

    LOGGER.info(f"Pan Processing for group: Running {pipeline} pipeline")
    LOGGER.info(f"start logging to {LOGFILE}")
    if "HOSTNAME" in os.environ.keys():
        hostname = os.environ["HOSTNAME"]
        LOGGER.info(f"Running on node: {hostname}")
    ipaddr = get_ip()
    LOGGER.info(f"IP Address of node: {ipaddr}")
    LOGGER.info("---------------------------------------------------")

    if "_proc"  in pipeline_class:
        nodename = pipeline_class.split("_")[0]
        panProcessor = panFactory.get_processflow(nodename,pipeline_class)
    else:
        panProcessor = panFactory.get_processflow(pipeline_class)

    if "script" in panProcessor.__name__:
        SCRIPTPARAMS = getParams(panpipe_labels,"SCRIPTPARAMS")
        SCRIPTCOMMAND = getParams(panpipe_labels,"SCRIPTCOMMAND")
                        
        PanProc = panProcessor(panpipe_labels,params=SCRIPTPARAMS,command=SCRIPTCOMMAND)
        PanProc.run()
    elif "_proc" in panProcessor.__name__:
        from inspect import signature
        curr_dir = os.getcwd()
        DIRECTPARAMS = getParams(panpipe_labels,"DIRECTPARAMS")
        if DIRECTPARAMS:
            DIRECTPARAMS = iterative_substitution(DIRECTPARAMS,panpipe_labels)
        else:
            DIRECTPARAMS={}
        valid_args = signature(panProcessor).parameters
        filtered_args = {k: v for k, v in DIRECTPARAMS.items() if k in valid_args}
        DIRECTSTARTDIR = getParams(panpipe_labels,"DIRECTSTARTDIR")
        if DIRECTSTARTDIR:
            if os.path.exists(DIRECTSTARTDIR):
                os.chdir(DIRECTSTARTDIR)

        panProcessor(panpipe_labels,**filtered_args)
        os.chdir(curr_dir)
    else:
        PanProc = panProcessor(panpipe_labels,pipeline_outdir, participant_label, name=pipeline,LOGGER=LOGGER,execution=execution_json, analysis_level = analysis_level, participant_project=xnat_projects, participant_session=session_label)
        PanProc.run()

    pipeline_end = datetime.datetime.now()
    LOGGER.info("---------------------------------------------------------------------------------")
    LOGGER.info(f"Group Processing Completed at: {str(pipeline_end)}")
    LOGGER.info("---------------------------------------------------------------------------------")
    pipeline_duration = pipeline_end - pipeline_start
    LOGGER.info(f"Group Processing Duration: {str(pipeline_duration)}")
    LOGGER.info("---------------------------------------------------------------------------------")

    LOGGER.debug(f"\nDump of configuration settings for group run of {pipeline}")
    LOGGER.debug("---------------------------------------------------------------------------------")
    LOGGER.debug(f"{panpipe_labels!r}")
    LOGGER.debug("\n------  environment dump -----------")
    LOGGER.debug(os.environ)
    
    ipaddr = get_ip()
    LOGGER.debug(f"\nIP Address of node")
    LOGGER.debug("-----------------------")
    LOGGER.debug(f"{ipaddr}")

def parse_params():
    parser = ArgumentParser(description="Pan pipelines")
    PathExists = partial(path_exists, parser=parser)
    parser.add_argument("config_file", type=PathExists, help="Pipeline Configuration File")
    parser.add_argument("pipeline", help="group subjects running pipeline")
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

    credentials = os.path.abspath(args.credentials)
    if os.path.exists(credentials):
        with open(credentials, 'r') as infile:
            cred_dict = json.load(infile)
            cred_user = getParams(cred_dict,"user")
            cred_password = getParams(cred_dict,"password")
    else:
        cred_user = "dummy_user"
        cred_password = "dummy_password"

    execution_json=getParams(panpipe_labels,"NIPYPE_CONFIG")
    if execution_json is None:
        execution_json = {} 

    participants_file = getParams(panpipe_labels,"PARTICIPANTS_FILE")
    bids_dir = getParams(panpipe_labels,"BIDS_DIR")

    participant_labels = getParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL")
    xnat_projects = getParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT")
    session_labels = getParams(panpipe_labels,"GROUP_SESSION_LABEL")
    xnat_shared_projects = getParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT")
    
    runGroupSubjects(participant_labels,xnat_projects, xnat_shared_projects, session_labels, pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json,analysis_level="group")



# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()