#!/usr/bin/env python
from panpipelines.utils.util_functions import *
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from functools import partial
import json
import pandas as pd
import os
import logging
import sys
import multiprocessing as mp
from functools import partial
from panpipelines.version import __version__
from panpipelines.single_subject import runSingleSubject
from panpipelines.group_subjects import runGroupSubjects

LOGGER = logger_setup("panpipelines", logging.DEBUG)
logger_addstdout(LOGGER, logging.INFO)

PROCESSING_OPTIONS=["slurm", "local"]


def parse_params():
    parser = ArgumentParser(description="Pan pipelines")
    PathExists = partial(path_exists, parser=parser)
    parser.add_argument("config_file", type=PathExists, help="Pipeline Configuration File")
    parser.add_argument("--pipeline_outdir", help="directory to place pipeline output")
    parser.add_argument("--participants_file", type=PathExists, help="list of participants")
    parser.add_argument("--sessions_file", type=PathExists, help="Comprehensive list of participants and sessions")
    parser.add_argument("--pipelines", nargs="+")
    parser.add_argument("--pipeline_match", nargs="+")
    parser.add_argument("--projects", nargs="+")
    parser.add_argument("--participant_label", nargs="*", type=drop_sub, help="filter by subject label (the sub- prefix can be removed).")
    parser.add_argument("--participant_exclusions", nargs="*", type=drop_sub, help="filter by subject label (the sub- prefix can be removed).")
    parser.add_argument("--session_label", nargs="*", type=drop_ses, help="filter by session label (the ses- prefix can be removed).")
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    return parser


def main():
    datelabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    job_ids={}

    parser=parse_params()
    args, unknown_args = parser.parse_known_args()

    panpipe_labels={}

    #  TO DO:
    #  In general need to think through how config variables are pulled in and overwritten at the 
    #  general and pipeline level. Current approach leaves a lot to be desired.
    #  We are lucky that pipeline_dir is really only referenced within the pipelines themselves and so we
    #  can get away with this here.
    #
    #  Envisage an approach whereby variables are referenced by a pipeline from both general and pipeline specific
    #  Using keyword in dictionary.
    #
    pipeline_outdir = args.pipeline_outdir
    if pipeline_outdir:
        pipeline_outdir = os.path.abspath(pipeline_outdir)
        panpipe_labels = updateParams(panpipe_labels,"PIPELINE_DIR",pipeline_outdir)

    panpipeconfig_file=str(args.config_file)
    panpipeconfig_json=None
    if os.path.exists(panpipeconfig_file):
        with open(panpipeconfig_file, 'r') as infile:
            panpipeconfig_json = json.load(infile)
    # obtain labels but do not process yet
    panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels,insert=True, postpone=True)

    if __file__:
        pkgdir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        panpipe_labels = insertParams(panpipe_labels,'PKG_DIR',pkgdir)
    panpipe_labels = insertParams(panpipe_labels,'PWD',str(os.getcwd()))

   # only need date label if pipeline outdir not provided. This helps with nipype caching for repeat runs
    if not pipeline_outdir:
        pipeline_outdir_suffix = "_" + datelabel
        pipeline_outdir_config = getParams(panpipe_labels,"PIPELINE_DIR")
        if pipeline_outdir_config:
            panpipe_labels = updateParams(panpipe_labels,"PIPELINE_DIR",pipeline_outdir_config + pipeline_outdir_suffix)
        else:
            pipeline_outdir_config = os.path.join(os.getcwd(),"pan_output" +  pipeline_outdir_suffix) 
            panpipe_labels = updateParams(panpipe_labels,"PIPELINE_DIR",pipeline_outdir_config)


    # Now we can resolve all the references based on precedence
    panpipe_labels = update_labels(panpipe_labels)

    pipeline_outdir=os.path.abspath(getParams(panpipe_labels,"PIPELINE_DIR"))
    if not os.path.exists(pipeline_outdir):
        os.makedirs(pipeline_outdir,exist_ok=True)

    # reproducible and slightly more robust name to faciliate nipype caching
    panlabel=os.path.basename(pipeline_outdir)

    LOGFILE=os.path.join(pipeline_outdir,f"{panlabel}_pan_processing.log")
    logger_addfile(LOGGER, LOGFILE, logging.DEBUG)

    LOGGER.info(f"Running {__file__} v{__version__}")
    LOGGER.info("Running Pan Processing")
    LOGGER.info(f"start logging to {LOGFILE}")

    label_key="CONFIG_FILE"
    label_value=panpipeconfig_file
    panpipe_labels = updateParams(panpipe_labels, label_key,label_value)

    credentials = os.path.abspath(getParams(panpipe_labels,"CREDENTIALS"))
    if credentials is not None and os.path.exists(credentials):
        with open(credentials, 'r') as infile:
            cred_dict = json.load(infile)
            cred_user = getParams(cred_dict,"user")
            cred_password = getParams(cred_dict,"password")
    else:
        cred_user = "dummy_user"
        cred_password = "dummy_password"

    participants_file = args.participants_file
    if args.participants_file is not None:
        participants_file=str(args.participants_file)
        label_key="PARTICIPANTS_FILE"
        label_value=participants_file
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        participants_file = getParams(panpipe_labels,"PARTICIPANTS_FILE")

    projects=args.projects
    if not projects:
        projects=["001_HML","002_HML","003_HML","004_HML"]
        LOGGER.info(f"--projects parameter not set. Using defaults {projects} to retrieve subjects and sessions from XNAT.")
    else:
        LOGGER.info(f"Retrieving subjects and sessions from XNAT project {projects}")

    TEMPLATEFLOW_HOME=getParams(panpipe_labels,"TEMPLATEFLOW_HOME")
    if TEMPLATEFLOW_HOME:
        LOGGER.info(f"Downloading an initial set of TemplateFlow templates for spaces MNI152NLin2009cAsym and MNI152NLin6Asym to {TEMPLATEFLOW_HOME}.")
        initTemplateFlow(TEMPLATEFLOW_HOME) 

    # if participants file doesn't exist then lets download it
    if not os.path.exists(participants_file):
        LOGGER.info(f"Participants file not found at {participants_file} - retrieving from XNAT. Please wait.")
        xnat_host = getParams(panpipe_labels,"XNAT_HOST")
        targetdir = os.path.dirname(participants_file)
        if not os.path.exists(targetdir):
            os.makedirs(targetdir)
        getBidsTSV(xnat_host,cred_user,cred_password,projects,"BIDS-AACAZ",targetdir,demographics=False)

    sessions_file = args.sessions_file
    if args.sessions_file is not None:
        sessions_file=str(args.sessions_file)
        label_key="SESSIONS_FILE"
        label_value=sessions_file
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        sessions_file = getParams(panpipe_labels,"SESSIONS_FILE")

    pipelines=args.pipelines
    if args.pipelines is not None:
        label_key="PIPELINES"
        label_value=pipelines
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        pipelines = getParams(panpipe_labels,"PIPELINES")

    pipeline_match=args.pipeline_match

    if not pipelines:
        LOGGER.info("No pipelines specified at command line.")
        pipelines = [p for p in panpipeconfig_json.keys() if p != "all_pipelines"]
        if pipeline_match:
            LOGGER.info(f"All pipelines matching {str(pipeline_match)} in configuration file will be run.")
            pipeline_select=[]
            for pipe_match in pipeline_match:
                pipeline_select.extend([p for p in pipelines if pipe_match in p])
            pipelines = pipeline_select
        else:
            LOGGER.info("All pipelines in configuration file will be run.")

    # Remove duplicates in pipeline list
    pipelines = list(set(pipelines))

    LOGGER.info(f"About to arrange pipelines by dependency. Pipeline list is {pipelines}")    
    pipelines = arrangePipelines(panpipeconfig_json,pipelines=pipelines)
    LOGGER.info(f"Pipelines arranged by dependency. Pipeline list is {pipelines}")    

    participant_label = args.participant_label
    if args.participant_label is not None:
        label_key="PARTICIPANTS"
        label_value=participant_label
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        participant_label = getParams(panpipe_labels,"PARTICIPANTS")

    participant_exclusions = args.participant_exclusions
    if not participant_exclusions:
        participant_exclusions = []

    session_label = args.session_label
    if args.session_label is not None:
        label_key="SESSION_LABEL"
        label_value=session_label
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        session_label = getParams(panpipe_labels,"SESSION_LABEL")


    LOGGER.info(f"Pipelines to be processed : {pipelines}")

    projectmap = get_projectmap(participant_label, participants_file,session_labels=session_label,sessions_file=sessions_file,subject_exclusions=participant_exclusions)
    participant_list = projectmap[0]
    project_list  = projectmap[1]
    session_list = projectmap[2]
    shared_project_list  = projectmap[3]

    # take snapshot of the runtime labels for all pipelines
    runtime_labels = panpipe_labels.copy()

    for pipeline in pipelines:
        LOGGER.info(f"Processing pipeline : {pipeline}")
        panpipe_labels = updateParams(panpipe_labels, "PIPELINE", pipeline)
        panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels,pipeline)

        analysis_level = getParams(panpipe_labels,"ANALYSIS_LEVEL")
        if analysis_level == "group":
            # rather rigid - but we foreshadow the worfflow directory here and use a param so it is useable
            wf_dir = f"<PIPELINE_DIR>/{pipeline}/group/{pipeline}_wf"
            panpipe_labels = updateParams(panpipe_labels,f"WORKFLOW_DIR",wf_dir)
        else:
            wf_dir = f"<PIPELINE_DIR>/{pipeline}/<PARTICIPANT_XNAT_PROJECT>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/{pipeline}_wf"
            panpipe_labels = updateParams(panpipe_labels,f"WORKFLOW_DIR",wf_dir)

        # We handle the <DEPENDENCY> key specially as this is a list that we need to resolve into DEPENDENCY1, DEPENDENCY2, ...DEPENDENCYN
        dependency_list = getParams(panpipe_labels,"DEPENDENCY")
        if dependency_list:
            depcount=1
            if isinstance(dependency_list,list):
                for dependency in dependency_list:
                    panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY{depcount}",dependency)
                    dependency_dir = f"<PIPELINE_DIR>/<DEPENDENCY{depcount}>/<PARTICIPANT_XNAT_PROJECT>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/<DEPENDENCY{depcount}>_wf"
                    panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY{depcount}_DIR",dependency_dir)
                    depcount = depcount + 1
            else:
                # can refere to single DEPENDENCY also as DEPENDENCY1
                panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY1",dependency_list)
                dependency_dir1 = f"<PIPELINE_DIR>/<DEPENDENCY{depcount}>/<PARTICIPANT_XNAT_PROJECT>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/<DEPENDENCY{depcount}>_wf"
                panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY{depcount}_DIR",dependency_dir1)
                dependency_dir = f"<PIPELINE_DIR>/<DEPENDENCY>/<PARTICIPANT_XNAT_PROJECT>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/<DEPENDENCY>_wf"
                panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY_DIR",dependency_dir)
            
        # Now we can resolve all the references based on precedence in the pipeline section
        panpipe_labels = update_labels(panpipe_labels)

        processing_environment=getParams(panpipe_labels,"PROCESSING_ENVIRONMENT") 

        if processing_environment is None  or processing_environment not in PROCESSING_OPTIONS:
            processing_environment = "slurm"

        if processing_environment == "slurm":
            analysis_node = getParams(panpipe_labels,"ANALYSIS_NODE")

            if analysis_level == "group":
                updateParams(panpipe_labels, "SLURM_TEMPLATE", getParams(panpipe_labels,"SLURM_GROUP_TEMPLATE"))
                if participant_label:
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL",participant_label)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT",project_list)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT",shared_project_list)
                    updateParams(panpipe_labels,"GROUP_SESSION_LABEL",session_list)
                else:
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL","*")
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT","*")
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT","*")
                    updateParams(panpipe_labels,"GROUP_SESSION_LABEL","*")

            else:
                updateParams(panpipe_labels, "SLURM_TEMPLATE", getParams(panpipe_labels,"SLURM_PARTICIPANT_TEMPLATE"))

            if analysis_node == "gpu":
                updateParams(panpipe_labels, "SLURM_HEADER", getParams(panpipe_labels,"SLURM_GPU_HEADER"))
            else:
                updateParams(panpipe_labels, "SLURM_HEADER", getParams(panpipe_labels,"SLURM_CPU_HEADER"))

            try:
                jobid = submit_script(participant_list, participants_file, pipeline, panpipe_labels,job_ids, analysis_level,projects_list = project_list, sessions_list=session_list, sessions_file = sessions_file, LOGGER=LOGGER,panlabel=panlabel)

                job_ids[pipeline]=jobid
            except Exception as ex:
                LOGGER.info(f"problems running pipeline {pipeline}. Details: {ex}")

        elif processing_environment == "local":
            pipeline_class = getParams(panpipe_labels,"PIPELINE_CLASS")
            if pipeline_class is None:
                pipeline_class = pipeline 

            #use_pipeline_desc = getParams(panpipe_labels,"USE_PIPELINE_DESC")
            #if use_pipeline_desc is None:
            #    use_pipeline_desc = "N"

            #pipeline_desc = getParams(panpipe_labels,"PIPELINE_DESC")
            #if pipeline_desc is None or use_pipeline_desc == "N":
            #    pipeline_desc = pipeline
            #else:
            #    pipeline_desc = "".join([x if x.isalnum() else "_" for x in pipeline_desc])  

            pipeline_outdir=os.path.join(getParams(panpipe_labels,"PIPELINE_DIR"),pipeline)
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

            bids_dir = getParams(panpipe_labels,"BIDS_DIR")

            execution_json=getParams(panpipe_labels,"NIPYPE_CONFIG")
            if execution_json is None:
                execution_json = {} 
            
            try:
                procs = getProcNums(panpipe_labels)

                if analysis_level == "participant":
                    # run serially if procs < 2
                    if procs > 1:
                        multiproc_zip = zip(participant_list,project_list,shared_project_list,session_list)
                        parrunSingleSubject=partial(runSingleSubject, pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json,analysis_level=analysis_level)
                        with mp.Pool(procs) as pool:
                            completedlist = pool.starmap(parrunSingleSubject,multiproc_zip)
                            pool.close()
                            pool.join()
                    else:
                        for part_count in range(len(participant_list)):
                            if session_list:
                                session_label= session_list[part_count]
                            else:
                                session_label=None
                            runSingleSubject(participant_list[part_count], project_list[part_count], shared_project_list[part_count],session_label,pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json,analysis_level=analysis_level)
                else:
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL",participant_list)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT",project_list)
                    updateParams(panpipe_labels,"GROUP_SESSION_LABEL",session_list)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT",shared_project_list)
                    runGroupSubjects(participant_list, project_list,shared_project_list,session_list,pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json,analysis_level=analysis_level)


            except Exception as ex:
                LOGGER.info(f"problems running pipeline {pipeline}. Details: {ex}")
 
        else:
            LOGGER.info(f"processing environment {processing_environment} not currently supported. Options are {PROCESSING_OPTIONS}.")

        # clear out and restore runtime labels for next pipeline
        panpipe_labels = {}
        panpipe_labels = add_labels(runtime_labels,panpipe_labels)
       
    LOGGER.info(f"All pipelines {pipelines} successfully run/submitted.")
    LOGGER.info(f"View logs at {LOGFILE}.")
    LOGGER.debug("\n------  environment dump -----------")
    LOGGER.debug(os.environ)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()