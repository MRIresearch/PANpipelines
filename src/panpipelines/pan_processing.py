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
from panpipelines.version import __version__
from panpipelines.single_subject import runSingleSubject
from panpipelines.group_subjects import runGroupSubjects
import shutil
import time

LOGGER = logger_setup("panpipelines", logging.DEBUG)
LOGGER.propagate = False
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
    parser.add_argument("--pipeline_exclude", nargs="+")
    parser.add_argument("--projects", nargs="+")
    parser.add_argument("--participant_label", nargs="*", type=drop_sub, help="filter by subject label (the sub- prefix can be removed).")
    parser.add_argument("--participant_label_fromfile", type=PathExists, help="participants from file.")    
    parser.add_argument("--incremental", default="False")
    parser.add_argument("--info_delta", default="False", help="what are the subjects that are left to process")
    parser.add_argument("--all_group", default="True")
    parser.add_argument("--force_bids_download",default="False")
    parser.add_argument("--run_dependent_pipelines",nargs="+")
    parser.add_argument("--run_interactive",default="True")
    parser.add_argument("--force_run",default="False")
    parser.add_argument("--participant_query", nargs="+", help="Apply query on pandas. works in exclusion to all other participant query filters")
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

    xnat_host = getParams(panpipe_labels,"XNAT_HOST")
    credentials = os.path.abspath(getParams(panpipe_labels,"CREDENTIALS"))
    if credentials is not None and os.path.exists(credentials):
        with open(credentials, 'r') as infile:
            cred_dict = json.load(infile)
            cred_user = getParams(cred_dict,"user")
            cred_password = getParams(cred_dict,"password")
    else:
        cred_user = "dummy_user"
        cred_password = "dummy_password"

    SHARED_PROJECT_LIST = getParams(panpipe_labels,"SHARED_PROJECT_LIST")
    if not SHARED_PROJECT_LIST:
        SHARED_PROJECT_LIST=["001_HML","002_HML","003_HML","004_HML"]

    PHANTOM_LIST= getParams(panpipe_labels,"PHANTOM_LIST")
    if not PHANTOM_LIST:
        PHANTOM_LIST=[]

    participants_file = args.participants_file
    if args.participants_file is not None:
        participants_file=str(args.participants_file)
        label_key="PARTICIPANTS_FILE"
        label_value=participants_file
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        participants_file = getParams(panpipe_labels,"PARTICIPANTS_FILE")

    sessions_file = args.sessions_file
    if args.sessions_file is not None:
        sessions_file=str(args.sessions_file)
        label_key="SESSIONS_FILE"
        label_value=sessions_file
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        sessions_file = getParams(panpipe_labels,"SESSIONS_FILE")

    if not participants_file:
        participants_file = os.path.join(pipeline_outdir,"xnat_participants_list.tsv")
        panpipe_labels = updateParams(panpipe_labels, "PARTICIPANTS_FILE",participants_file)

    if not sessions_file:
        sessions_file = os.path.join(pipeline_outdir,"xnat_participants_list.tsv")
        panpipe_labels = updateParams(panpipe_labels, "SESSIONS_FILE",sessions_file)

    projects=args.projects
    if not projects:
        projects=["001_HML","002_HML","003_HML","004_HML"]
        LOGGER.info(f"--projects parameter not set. Using defaults {projects} to retrieve subjects and sessions from XNAT.")
    else:
        LOGGER.info(f"Retrieving subjects and sessions from XNAT project {projects}")

    INFO_DELTA = isTrue(args.info_delta)
    ALL_GROUP = isTrue(args.all_group)
    if not ALL_GROUP:
        panpipe_labels = updateParams(panpipe_labels,"ALL_GROUP","N")
    else:
        panpipe_labels = updateParams(panpipe_labels,"ALL_GROUP","Y")       
    INCREMENTAL = isTrue(args.incremental)

    bids_incremental_dir = getParams(panpipe_labels,"BIDS_INCREMENTAL_DIR")
    if not bids_incremental_dir:
        sinkdir = substitute_labels(getParams(panpipe_labels,"SINKDIR_GROUP"),panpipe_labels)
        if not sinkdir:
            derivatives_dir = substitute_labels(getParams(panpipe_labels,"DERIVATIVES_DIR"),panpipe_labels)
            if not derivatives_dir:
                bids_incremental_dir = os.path.join(pipeline_outdir,"derivatives","output_tables","bids_incremental") 
            else:
                bids_incremental_dir = os.path.join(pipeline_outdir,"output_tables","bids_incremental") 
        else:
            bids_incremental_dir = os.path.join(os.path.dirname(sinkdir),"bids_incremental")
    
    if not os.path.exists(bids_incremental_dir):
        os.makedirs(bids_incremental_dir,exist_ok=True)

    if INFO_DELTA:
        new_targetdir=bids_incremental_dir
        info_delta_suffix = f"latest-{datelabel}"
        new_participants_file = newfile(outputdir=new_targetdir, assocfile=participants_file,suffix=info_delta_suffix )

        LOGGER.info(f"Comparing latest participants file on XNAT with current participants file to determine subjects that require downloading.")
        LOGGER.info(f"Downloading latest participants file to {new_targetdir} with suffix of {info_delta_suffix}")
        getBidsTSV(xnat_host,cred_user,cred_password,projects,"BIDS-AACAZ",new_participants_file,demographics=False,shared_project_list=SHARED_PROJECT_LIST,phantom_list=PHANTOM_LIST)
        
        df1 = pd.read_table(new_participants_file,sep="\t")
        participants_list1 = df1["hml_id"].tolist()
        df2 = pd.read_table(participants_file,sep="\t")
        participants_list2 = df2["hml_id"].tolist()
        participant_incremental = [ drop_sub(x) for x in list(set(participants_list1).difference(set(participants_list2)))]
        LOGGER.info(f"Incremental participants found {participant_incremental}")
        mask = df1["hml_id"].isin(participant_incremental)
        incremental_df = df1[mask]
        incremental_tsv = newfile(assocfile=new_participants_file,suffix="delta")
        LOGGER.info(f"Saving delta participant information to {incremental_tsv}.")
        incremental_df.to_csv(incremental_tsv,sep="\t",header=True, index=False)
        panpipe_labels = updateParams(panpipe_labels,"INCREMENTAL_PARTICIPANTS_FILE",incremental_tsv)
        LOGGER.info(f"Quitting.")
        sys.exit(0)


    TEMPLATEFLOW_HOME=getParams(panpipe_labels,"TEMPLATEFLOW_HOME")
    if TEMPLATEFLOW_HOME:
        LOGGER.info(f"Downloading an initial set of TemplateFlow templates for spaces MNI152NLin2009cAsym and MNI152NLin6Asym to {TEMPLATEFLOW_HOME}.")
        initTemplateFlow(TEMPLATEFLOW_HOME)

    RUN_INTERACTIVE=isTrue(args.run_interactive)
    dependent_pipelines = args.run_dependent_pipelines
    if dependent_pipelines:
        RUN_DEPENDENT_PIPELINES = True
    else:
        RUN_DEPENDENT_PIPELINES = False
        dependent_pipelines=[]

    FORCE_BIDS_DOWNLOAD = isTrue(args.force_bids_download)
    if FORCE_BIDS_DOWNLOAD:
        panpipe_labels = updateParams(panpipe_labels,"FORCE_BIDS_DOWNLOAD","Y")
        LOGGER.info(f"FORCE_BIDS_DOWNLOAD set to Y")

    FORCE_RUN = isTrue(args.force_run)
    if FORCE_RUN:
        panpipe_labels = updateParams(panpipe_labels,"FORCE_RUN","Y")
        LOGGER.info(f"FORCE_RUN set to Y. All selected pipelines will be forced to rerun")

    if INCREMENTAL:
        LOGGER.info("Running panprocessing in incremental mode.")
        if not os.path.exists(participants_file):
            LOGGER.info(f"Participants file {participants_file} not present. Cannot run processing in incremental mode")
            INCREMENTAL= False
        else:
            old_participants_file=newfile(assocfile=participants_file,suffix=datelabel)
            shutil.move(participants_file,old_participants_file)
            old_sessions_file=newfile(assocfile=sessions_file,suffix=datelabel)
            shutil.move(sessions_file,old_sessions_file)
            bids_participant_file=os.path.join(getParams(panpipe_labels,"BIDS_DIR"),"participants.tsv")
            backup_participant_file= newfile(assocfile=bids_participant_file,suffix=datelabel)
            shutil.copy(bids_participant_file,backup_participant_file)

    # if participants file doesn't exist then lets download it
    if not os.path.exists(sessions_file):
        if not os.path.exists(participants_file):
            LOGGER.info(f"Participants file not found at {participants_file} - retrieving from XNAT. Please wait.")
            targetdir = os.path.dirname(participants_file)
            if not os.path.exists(targetdir):
                os.makedirs(targetdir,exist_ok=True)

        if not os.path.exists(sessions_file):
            LOGGER.info(f"Sessions file not found at {sessions_file} - retrieving from XNAT. Please wait.")
            targetdir = os.path.dirname(sessions_file)
            if not os.path.exists(targetdir):
                os.makedirs(targetdir,exist_ok=True)

        getBidsTSV(xnat_host,cred_user,cred_password,projects,"BIDS-AACAZ",participants_file,demographics=False,shared_project_list=SHARED_PROJECT_LIST,phantom_list=PHANTOM_LIST,sessionsTSV=sessions_file)


    pipelines=args.pipelines
    if args.pipelines is not None:
        label_key="PIPELINES"
        label_value=pipelines
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        pipelines = getParams(panpipe_labels,"PIPELINES")

    if not pipelines:
        pipelines=[]

    pipeline_match=args.pipeline_match
    pipeline_exclude=args.pipeline_exclude

    ALL_PIPELINES=[p for p in panpipeconfig_json.keys() if p != "all_pipelines"]
    if not pipelines and not dependent_pipelines:
        LOGGER.info("No pipelines specified at command line.")
        pipelines = ALL_PIPELINES
        if pipeline_match:
            LOGGER.info(f"All pipelines matching {str(pipeline_match)} in configuration file will be run.")
            pipeline_select=[]
            for pipe_match in pipeline_match:
                pipeline_select.extend([p for p in pipelines if pipe_match in p])
            pipelines = pipeline_select
        else:
            LOGGER.info("All pipelines in configuration file will be run.")

    if RUN_DEPENDENT_PIPELINES:
        pipelines.extend(get_dependent_pipelines(panpipeconfig_json,dependent_pipelines,ALL_PIPELINES))
        panpipe_labels = updateParams(panpipe_labels, "RUN_DEPENDENT_PIPELINES","Y")

    if pipeline_exclude and pipelines:
        LOGGER.info(f"Excluding pipelines {pipeline_exclude} from this run.")
        pipelines = list(set(pipelines) - set(pipeline_exclude))

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

    participant_label_fromfile = args.participant_label_fromfile
    if participant_label_fromfile:
        with open(participant_label_fromfile, 'r') as infile:
            parts = infile.read()
        split_parts = parts.split("\n")
        split_parts_valid = [x for x in split_parts if x]

        if split_parts_valid:
            label_key="PARTICIPANTS"
            participant_label = split_parts_valid
            label_value=participant_label
            panpipe_labels = updateParams(panpipe_labels, label_key,label_value)


    participant_query = args.participant_query
    if not participant_query:
        participant_query = ""
    else:
        participant_query = " ".join(participant_query)

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
        if not session_label:
            session_label="ALL_SESSIONS"
            panpipe_labels = updateParams(panpipe_labels, "SESSION_LABEL",session_label)

    if INCREMENTAL:
        LOGGER.info("Running in incremental mode. Identifying participants to run")
        df1 = pd.read_table(participants_file,sep="\t")
        participants_list1 = df1["hml_id"].tolist()
        df2 = pd.read_table(old_participants_file,sep="\t")
        participants_list2 = df2["hml_id"].tolist()
        participant_incremental = [ drop_sub(x) for x in list(set(participants_list1).difference(set(participants_list2)))]
        LOGGER.info(f"Incremental participants found {participant_incremental}")

        new_targetdir=bids_incremental_dir
        info_delta_suffix = f"latest-{datelabel}"
        mask = df1["hml_id"].isin(participant_incremental)
        incremental_df = df1[mask]
        incremental_tsv = newfile(outputdir= new_targetdir, assocfile=participants_file,suffix=info_delta_suffix + "-" + "delta")
        LOGGER.info(f"Saving delta participant information to {incremental_tsv}.")
        incremental_df.to_csv(incremental_tsv,sep="\t",header=True, index=False)
        panpipe_labels = updateParams(panpipe_labels,"INCREMENTAL_PARTICIPANTS_FILE",incremental_tsv)

        participant_label.extend(participant_incremental)
        LOGGER.info(f"Participants to process {participant_label}")

    # take snapshot of the runtime labels for all pipelines
    runtime_labels = panpipe_labels.copy()

    if INCREMENTAL:
        if not pipelines:
            LOGGER.info(f"Running in incremental mode but no pipelines selected. Will run the dummy_panpipeline and ftp_upload_pan script if they are not explictly excluded")
            if "dummy" not in pipeline_exclude:
                pipelines.add("dummy")
            
            if "ftp_upload_bids" not in pipeline_exclude:
                pipelines.add("ftp_upload_bids")

    if not participant_query:            
        LOGGER.info(f"participants to be processed:\n {participant_label}.\n Note that subject exclusions will be applied at the pipeline level.\n")
    else:
        projectmap = get_projectmap_query(sessions_file,participant_query)
        participant_list = projectmap[0]
        LOGGER.info(f"participants to be processed:\n {participant_list}.\n Note that subject exclusions will be applied at the pipeline level.\n")
    time.sleep(1)
    LOGGER.info(f"Pipelines to be processed :\n {pipelines}\n")
    time.sleep(1)

    key=""
    if RUN_INTERACTIVE:
        key=input("press c to continue, q to exit")
    while RUN_INTERACTIVE and not key.upper() == "C":
        if key.upper() == "Q":
            sys.exit()
        key=input()
        
    for pipeline in pipelines:

        subject_exclusions=[]
        subject_exclusions.extend(participant_exclusions)

        pipeline_panpipe_labels={}
        pipeline_panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,pipeline_panpipe_labels,pipeline)
        
        pipeline_exclusions = getParams(pipeline_panpipe_labels,"PARTICIPANT_PIPELINE_EXCLUSIONS")
        if not pipeline_exclusions:
            pipeline_exclusions=[]
        subject_exclusions.extend(pipeline_exclusions) 
        panpipe_labels = updateParams(panpipe_labels,"EXCLUDED_PARTICIPANTS",subject_exclusions)

        if not participant_query:
            projectmap = get_projectmap(participant_label, participants_file,session_labels=session_label,sessions_file=sessions_file,subject_exclusions=subject_exclusions)
        else:
            projectmap = get_projectmap_query(sessions_file,participant_query,subject_exclusions=subject_exclusions)
        participant_list = projectmap[0]
        panpipe_labels = updateParams(panpipe_labels, "PARTICIPANTS",participant_list)
        project_list  = projectmap[1]
        session_list = projectmap[2]
        shared_project_list  = projectmap[3]

        # obtain mappings for all subjects which will be handy for incremental
        projectmap_all = get_projectmap(["ALL_SUBJECTS"],participants_file,session_labels=session_label,sessions_file=sessions_file,subject_exclusions=subject_exclusions)
        participant_list_all = projectmap_all[0]
        project_list_all  = projectmap_all[1]
        session_list_all = projectmap_all[2]
        shared_project_list_all = projectmap_all[3]

        LOGGER.info(f"Processing pipeline : {pipeline}")
        panpipe_labels = updateParams(panpipe_labels, "PIPELINE", pipeline)
        panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels,pipeline)

        ALL_GROUP = isTrue(getParams(panpipe_labels,"ALL_GROUP"))

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
            if not isinstance(dependency_list,list):
                dependency_list=[dependency_list]
                # can refer to single DEPENDENCY also as DEPENDENCY1
                dependency_dir = f"<PIPELINE_DIR>/<DEPENDENCY>/<PARTICIPANT_XNAT_PROJECT>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/<DEPENDENCY>_wf"
                panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY_DIR",dependency_dir)

            depcount=1

            for dependency in dependency_list:
                panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY{depcount}",dependency)
                dependency_dir = f"<PIPELINE_DIR>/<DEPENDENCY{depcount}>/<PARTICIPANT_XNAT_PROJECT>/sub-<PARTICIPANT_LABEL>/ses-<PARTICIPANT_SESSION>/<DEPENDENCY{depcount}>_wf"
                panpipe_labels = updateParams(panpipe_labels,f"DEPENDENCY{depcount}_DIR",dependency_dir)
                depcount = depcount + 1
        
        # Now we can resolve all the references based on precedence in the pipeline section
        panpipe_labels = update_labels(panpipe_labels)

        processing_environment=getParams(panpipe_labels,"PROCESSING_ENVIRONMENT") 

        if processing_environment is None  or processing_environment not in PROCESSING_OPTIONS:
            processing_environment = "slurm"

        if processing_environment == "slurm":
            analysis_node = getParams(panpipe_labels,"ANALYSIS_NODE")

            if analysis_level == "group":
                updateParams(panpipe_labels, "SLURM_TEMPLATE", getParams(panpipe_labels,"SLURM_GROUP_TEMPLATE"))
                if participant_list and not ALL_GROUP:
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL",participant_list)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT",project_list)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT",shared_project_list)
                    updateParams(panpipe_labels,"GROUP_SESSION_LABEL",session_list)
                else:
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL",participant_list_all)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT",project_list_all)
                    updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT",shared_project_list_all)
                    updateParams(panpipe_labels,"GROUP_SESSION_LABEL",session_list_all)

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
                    if ALL_GROUP:
                        updateParams(panpipe_labels,"GROUP_PARTICIPANTS_LABEL",participant_list_all)
                        updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_PROJECT",project_list_all)
                        updateParams(panpipe_labels,"GROUP_SESSION_LABEL",session_list_all)
                        updateParams(panpipe_labels,"GROUP_PARTICIPANTS_XNAT_SHARED_PROJECT",shared_project_list_all)
                        runGroupSubjects(participant_list_all, project_list_all,shared_project_list_all,session_list_all,pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json,analysis_level=analysis_level)
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