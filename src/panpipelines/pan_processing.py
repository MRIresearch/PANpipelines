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

PROCESSING_OPTIONS=["slurm", "local"]

def parse_params():
    parser = ArgumentParser(description="Pan pipelines")
    PathExists = partial(path_exists, parser=parser)
    parser.add_argument("config_file", type=PathExists, help="Pipeline Configuration File")
    parser.add_argument("--participants_file", type=PathExists, help="list of participants")
    parser.add_argument("--pipelines", nargs="+")
    parser.add_argument("--participant_label", nargs="*", type=drop_sub, help="filter by subject label (the sub- prefix can be removed).")
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    return parser


def main():
    datelabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    job_ids={}

    parser=parse_params()
    args, unknown_args = parser.parse_known_args()

    print(f"Running {__file__} v{__version__}")

    runtime_labels={}
    panpipe_labels={}
    panpipe_labels = updateParams(panpipe_labels,'PWD',str(os.getcwd()))
    runtime_labels = updateParams(runtime_labels,'PWD',str(os.getcwd()))
    panpipe_labels = updateParams(panpipe_labels,'DATE_LABEL',datelabel)
    runtime_labels = updateParams(runtime_labels,'DATE_LABEL',datelabel)

    panpipeconfig_file=str(args.config_file)
    panpipeconfig_json=None
    if os.path.exists(panpipeconfig_file):
        with open(panpipeconfig_file, 'r') as infile:
            panpipeconfig_json = json.load(infile)
    panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels)

    pipeline_outdir=os.path.join(getParams(panpipe_labels,"PIPELINE_DIR"))
    if not os.path.exists(pipeline_outdir):
        os.makedirs(pipeline_outdir)

    LOGFILE=os.path.join(pipeline_outdir,f"{datelabel}_pan_processing.log")
    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logging.info("Running Pan Processing")
    logging.info(f"start logging to {LOGFILE}")

    label_key="CONFIG_FILE"
    label_value=panpipeconfig_file
    panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    runtime_labels = updateParams(runtime_labels,"CONFIG_FILE",getParams(panpipe_labels,"CONFIG_FILE"))

    participants_file = args.participants_file
    if args.participants_file is not None:
        participants_file=str(args.participants_file)
        label_key="PARTICIPANTS_FILE"
        label_value=participants_file
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        participants_file = getParams(panpipe_labels,"PARTICIPANTS_FILE")

    pipelines=args.pipelines
    if args.pipelines is not None:
        label_key="PIPELINES"
        label_value=pipelines
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        participant_label = getParams(panpipe_labels,"PARTICIPANT_LABEL")

    runtime_labels = updateParams(runtime_labels,"PARTICIPANT_LABEL",getParams(panpipe_labels,"PARTICIPANT_LABEL"))

    participant_label = args.participant_label
    if args.participant_label is not None:
        label_key="PARTICIPANT_LABEL"
        label_value=participant_label
        panpipe_labels = updateParams(panpipe_labels, label_key,label_value)
    else:
        pipelines = getParams(panpipe_labels,"PIPELINES")

    runtime_labels = updateParams(runtime_labels,"PIPELINES",getParams(panpipe_labels,"PIPELINES"))

    logging.info(f"Pipelines to be processed : {pipelines}")

    for pipeline in pipelines:
        logging.info(f"Processing pipeline : {pipeline}")
        updateParams(panpipe_labels, "PIPELINE", pipeline)
        panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels,pipeline)
        analysis_level = getParams(panpipe_labels,"ANALYSIS_LEVEL")

        processing_environment=getParams(panpipe_labels,"PROCESSING_ENVIRONMENT") 

        if processing_environment is None  or processing_environment not in PROCESSING_OPTIONS:
            processing_environment = "slurm"

        if processing_environment == "slurm":
            analysis_node = getParams(panpipe_labels,"ANALYSIS_NODE")

            if analysis_level == "group":
                updateParams(panpipe_labels, "SLURM_TEMPLATE", getParams(panpipe_labels,"SLURM_GROUP_TEMPLATE"))
            else:
                updateParams(panpipe_labels, "SLURM_TEMPLATE", getParams(panpipe_labels,"SLURM_PARTICIPANT_TEMPLATE"))

            if analysis_node == "gpu":
                updateParams(panpipe_labels, "SLURM_HEADER", getParams(panpipe_labels,"SLURM_GPU_HEADER"))
            else:
                updateParams(panpipe_labels, "SLURM_HEADER", getParams(panpipe_labels,"SLURM_CPU_HEADER"))

            # analysis_level seems somewhat redundant at the script level as we pass in the required SLURM TEMPLATE
            # perhaps we can replace <<PYTHON_SCRIPT>> with single_subject.py or group.py depending on level?
            jobid = submit_script(participant_label, participants_file, pipeline, panpipe_labels,job_ids, analysis_level, logging)

            job_ids[pipeline]=jobid

        elif processing_environment == "local":

            if analysis_level == "participant":

                pipeline_class = getParams(panpipe_labels,"PIPELINE_CLASS")
                if pipeline_class is None:
                    pipeline_class = pipeline 

                pipeline_outdir=os.path.join(getParams(panpipe_labels,"PIPELINE_DIR"),pipeline)
                if not os.path.exists(pipeline_outdir):
                    os.makedirs(pipeline_outdir,exist_ok=True)

                bids_dir = getParams(panpipe_labels,"BIDS_DIR")

                credentials = os.path.abspath(getParams(panpipe_labels,"CREDENTIALS"))
                if credentials is not None and os.path.exists(credentials):
                    with open(credentials, 'r') as infile:
                        cred_dict = json.load(infile)
                        cred_user = getParams(cred_dict,"user")
                        cred_password = getParams(cred_dict,"password")

                execution_json=getParams(panpipe_labels,"NIPYPE_CONFIG")
                if execution_json is None:
                    execution_json = {} 

                procs = getProcNums(panpipe_labels)
                projectmap = get_projectmap(participant_label, participants_file)
                participant_list = projectmap[0]
                project_list  = projectmap[1]

                # run serially if procs < 2
                if procs > 1:
                    parrunSingleSubject=partial(runSingleSubject, pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json)
                    with mp.Pool(procs) as pool:
                        completedlist = pool.starmap(parrunSingleSubject,zip(participant_list,project_list))
                        pool.close()
                        pool.join()
                else:
                    for part_count in range(len(participant_list)):
                        runSingleSubject(participant_list[part_count], project_list[part_count],pipeline=pipeline, pipeline_class=pipeline_class, pipeline_outdir=pipeline_outdir, panpipe_labels=panpipe_labels,bids_dir=bids_dir,cred_user=cred_user,cred_password=cred_password, execution_json=execution_json)


            else:
                # need to implement group analysis here
                pass

        else:
            logging.info(f"processing environment {processing_environment} not currently supported. Options are {PROCESSING_OPTIONS}.")


        panpipe_labels = remove_labels(panpipe_labels,panpipeconfig_json,pipeline)
        panpipe_labels = removeParam(panpipe_labels, "PIPELINE")
        panpipe_labels = process_labels(panpipeconfig_json,panpipeconfig_file,panpipe_labels)
        panpipe_labels = add_labels(runtime_labels,panpipe_labels)
       
    logging.info(f"All pipelines {pipelines} successfully submitted.")
    logging.info(f"View logs at {LOGFILE}.")
    logging.debug("------  environment dump -----------")
    logging.debug(os.environ)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()