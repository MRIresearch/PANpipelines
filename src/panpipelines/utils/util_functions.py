import re
from pathlib import Path
import os
import numpy as np
import pandas as pd
import datetime
import subprocess
import shlex
import json
import glob
import tempfile
import math
import multiprocessing as mp
import logging
import nibabel as nib
import shutil
from panpipelines.utils.transformer import *
import sys
from nipype import logging as nlogging
import fcntl
import time
from bids import BIDSLayout
from collections import OrderedDict

UTLOGGER=nlogging.getLogger('nipype.utils')

def logger_setup(logname, loglevel):
    LOGGER = logging.getLogger(logname)
    LOGGER.setLevel(loglevel)
    return LOGGER

def logger_addstdout(LOGGER, loglevel):
    formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(loglevel)
    stdout_handler.setFormatter(formatter)
    LOGGER.addHandler(stdout_handler)

def logger_addfile(LOGGER, LOGFILE, loglevel):
    formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')
    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setLevel(loglevel)
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)

def nipype_loggers_setup(loglevel,LOGFILE,file_loglevel):
    WFLOGGER=nlogging.getLogger('nipype.workflow')
    IFLOGGER=nlogging.getLogger('nipype.interface')
    UTLOGGER=nlogging.getLogger('nipype.utils')

    formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(loglevel)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setLevel(file_loglevel)
    file_handler.setFormatter(formatter)

    if len(WFLOGGER.handlers) < 1:
        WFLOGGER.addHandler(stdout_handler)
        WFLOGGER.addHandler(file_handler)

    if len(IFLOGGER.handlers) < 1:
        IFLOGGER.addHandler(stdout_handler)
        IFLOGGER.addHandler(file_handler)

    if len(UTLOGGER.handlers) < 1:
        UTLOGGER.addHandler(stdout_handler)
        UTLOGGER.addHandler(file_handler)


def path_exists(path, parser):
    """Ensure a given path exists."""
    if path is None or not Path(path).exists():
        raise parser.error(f"Path does not exist: <{path}>.")
    return Path(path).expanduser().absolute()

def drop_sub(value):
    return re.sub(r"^sub-", "", str(value))

def drop_ses(value):
    return re.sub(r"^ses-", "", str(value))

def isTrue(arg):
    return arg is not None and (arg == 'Y' or arg == 'y' or arg == '1' or arg == 'True' or arg == 'true' or arg == True)

def special_substitution(expression,pardict, key,unbracedKey):
    if expression is not None and key is not None and pardict is not None:
        if key=="<XNAT_USER>":
            credentials = os.path.abspath(getParams(pardict,"CREDENTIALS"))
            if credentials is not None and os.path.exists(credentials):
                with open(credentials, 'r') as infile:
                    cred_dict = json.load(infile)
                    if "user" in cred_dict.keys():
                        cred_user = getParams(cred_dict,"user")
                        expression = expression.replace(key,cred_user) 
        elif key=="<XNAT_PASSWORD>":
            credentials = os.path.abspath(getParams(pardict,"CREDENTIALS"))
            if credentials is not None and os.path.exists(credentials):
                with open(credentials, 'r') as infile:
                    cred_dict = json.load(infile)
                    if "password" in cred_dict.keys():
                        cred_password = getParams(cred_dict,"password")
                        expression = expression.replace(key,cred_password)
        elif unbracedKey in pardict and isinstance(pardict[unbracedKey],list):
            list_string = " ".join(pardict[unbracedKey])
            expression = expression.replace(key,list_string)
    return expression

def getParams(pardict, key, update=True):
    if key is not None and pardict is not None:
        if key in pardict:
            if update:
                updateParams(pardict,key,pardict[key])
                return pardict[key] 
            else:
                return pardict[key]
    return None

def insertParams(pardict, key, value, postpone=False):
    """ Insert key:value pair into dictionary if it does not already exist.

    Parameters:
    -----------
    pardict  : The dictionary reference
    key      : Key to insert
    value    : value to associate with key
    postpone : bool , default False; If True then do not substitute variables enclosed by <>
    
    Return:
    -------
    Reference to Dictionary is returned

    """
    if key is not None and pardict is not None and value is not None and key not in pardict.keys():
        if not postpone:
            pardict[key]=substitute_labels(value,pardict)
        else:
            pardict[key]=value
    return pardict 

def updateParams(pardict, key, value, postpone=False):
    if key is not None and pardict is not None and value is not None:
        if not postpone:
            pardict[key]=substitute_labels(value,pardict)
        else:
            pardict[key]=value
    return pardict 

def removeParam(pardict,key):
    if key is not None and pardict is not None and key in pardict.keys():
        pardict.pop(key)

    return pardict

def export_labels(panpipe_labels,export_file):
    with open(export_file,"w") as outfile:
        json.dump(panpipe_labels,outfile,indent=2)

def special_substitute_labels(expression,panpipe_labels,exceptions=[]):
    if isinstance(expression,str):
        braced_vars = re.findall(r'\<.*?\>',expression)
        for braced_var in braced_vars:
            unbraced_var = braced_var.replace('<','').replace('>','')
            lookup_var = getParams(panpipe_labels,unbraced_var)
            if isinstance(lookup_var,str) and lookup_var is not None and unbraced_var not in exceptions:
                expression = expression.replace(braced_var,lookup_var) 
            else:
                expression = special_substitution(expression, panpipe_labels,braced_var,unbraced_var)           
    return expression

def substitute_labels(expression,panpipe_labels,exceptions=[]):
    if isinstance(expression,str):
        braced_vars = re.findall(r'\<.*?\>',expression)
        for braced_var in braced_vars:
            unbraced_var = braced_var.replace('<','').replace('>','')
            lookup_var = getParams(panpipe_labels,unbraced_var)
            if isinstance(lookup_var,str) and lookup_var is not None and unbraced_var not in exceptions:
                expression = expression.replace(braced_var,lookup_var)            
    return expression

def remove_labels(labels_dict, config_json,pipeline):  
    # Process Labels

    try:
        LABELKEY=pipeline
        LABELS=config_json[LABELKEY]
    except KeyError:
        print("'{}' not defined in labels dictionary".format(LABELKEY))
        return labels_dict

    for itemkey,itemvalue in LABELS.items():
            removeParam(labels_dict,itemkey)

    return labels_dict

def add_labels(config_dict,labels_dict,postpone=False):  
    # Process Labels
    for itemkey,itemvalue in config_dict.items():
            updateParams(labels_dict,itemkey,itemvalue,postpone=postpone)

    return labels_dict

def process_labels(config_json,config_file,labels_dict,pipeline=None,uselabel=True,insert=False,postpone=False):  
    # Process Labels

    try:
        if pipeline is None or pipeline=="":
            LABELKEY="all_pipelines"
        else:
            LABELKEY=pipeline

        if uselabel:
            LABELS=config_json[LABELKEY]
        else:
            LABELS=config_json
    except KeyError:
        print("'{}' not defined in config file {}".format(LABELKEY,str(config_file)))
        return labels_dict

    for itemkey,itemvalue in LABELS.items():
        if insert:
            insertParams(labels_dict,itemkey,itemvalue,postpone=postpone)
        else:
            updateParams(labels_dict,itemkey,itemvalue,postpone=postpone)

    return labels_dict
    

def update_labels(labels_dict):  
    # update Labels
    varkeys = list(labels_dict.keys())
    ordered_varkeys = order_varkeys(varkeys,labels_dict,varkeys.copy())

    for itemkey in ordered_varkeys:
        itemvalue = labels_dict[itemkey]
        labels_dict[itemkey]=substitute_labels(itemvalue,labels_dict)

    return labels_dict

def order_varkeys(varkeys, labels_dict, orderedkeys):
    for key in varkeys:
        if key in labels_dict.keys():
            keyindex = orderedkeys.index(key)
            if isinstance(labels_dict[key],str):
                braced_vars = re.findall(r'\<.*?\>',labels_dict[key])
                if braced_vars:
                    for braced_var in braced_vars:
                        unbraced_var = braced_var.replace('<','').replace('>','')
                        if unbraced_var in orderedkeys:
                            varkeyindex = orderedkeys.index(unbraced_var)
                            if varkeyindex > keyindex:
                                orderedkeys.insert(keyindex,unbraced_var)
                                orderedkeys.pop(varkeyindex+1)
        
    return orderedkeys


def process_dict(config_dict,labels):  
    for configkey,configvalue in labels.items():
        try:
            CONFIG=config_dict[configkey]
            for itemkey,itemvalue in configvalue.items():
                try:
                    CONFIG[itemkey]=itemvalue
                except KeyError:
                    print("{} not defined in config dict using key {}".format(str(itemkey),configkey))
                    continue

            config_dict[configkey]=CONFIG

        except KeyError:
            print("{} not defined in config dict".format(str(configkey)))
            continue

    return config_dict


def process_fsl_glm(panpipe_labels):
    fsldesign_text = getParams(panpipe_labels,"TEXT_FSL_DESIGN")
    fslcontrast_text = getParams(panpipe_labels,"TEXT_FSL_CONTRAST")
    fslftest_text = getParams(panpipe_labels,"TEXT_FSL_FTEST")

    command_base, container = getContainer(panpipe_labels,nodename="process_fsl_glm",SPECIFIC="NEURO_CONTAINER")

    if os.path.exists(fsldesign_text):
        designdir=os.path.dirname(fsldesign_text)
        outputdir=os.path.join(designdir,"fslglm")

        df = pd.read_table(fsldesign_text,sep=",",header=None)

        if not os.path.isdir(outputdir):
            os.makedirs(outputdir)

        newfsldesign_text=os.path.join(designdir,os.path.basename(fsldesign_text).split(".")[0] + '.textmat')
        newfsldesign=os.path.join(outputdir,os.path.basename(fsldesign_text).split(".")[0] + '.mat')

        df.pop(0)
        df.to_csv(newfsldesign_text,sep=" ",header=False, index=False)

        command=f"{command_base}"\
            " Text2Vest " + newfsldesign_text + " " + newfsldesign
        evaluated_command=substitute_labels(command, panpipe_labels)
        results = runCommand(evaluated_command)
        panpipe_labels = updateParams(panpipe_labels,"FSL_DESIGN",newfsldesign)


        if fslcontrast_text is not None and os.path.exists(fslcontrast_text):
            newfslcontrast=os.path.join(outputdir,os.path.basename(fslcontrast_text).split(".")[0] + '.con')
            command=f"{command_base}"\
            " Text2Vest " + fslcontrast_text + " " + newfslcontrast
            evaluated_command=substitute_labels(command, panpipe_labels)
            results = runCommand(evaluated_command)
            panpipe_labels = updateParams(panpipe_labels,"FSL_CONTRAST",newfslcontrast)
        else:
            print("TEXT_FSL_CONTRAST Contrast not defined or doed not exist")


        if fslftest_text is not None and os.path.exists(fslftest_text):
            newfslftest=os.path.join(outputdir,os.path.basename(fslftest_text).split(".")[0] + '.fts')
            command=f"{command_base}"\
            " Text2Vest " + fslftest_text + " " + newfslftest
            evaluated_command=substitute_labels(command, panpipe_labels)
            results = runCommand(evaluated_command)
            panpipe_labels = updateParams(panpipe_labels,"FSL_FTEST",newfslftest)
        else:
            print("TEXT_FSL_FTEST Ftest not defined or doed not exist")

    else:
        print("TEXT_FSL_DESIGN Design not defined or doed not exist")

def save_image_to_disk(in_file,newimgdata,output_file):
    from nilearn.image import new_img_like
    import nibabel
    
    img = nibabel.load(in_file)
    img_dtype = img.header.get_data_dtype()

    data_to_save=newimgdata.astype(img_dtype)

    new_img=new_img_like(img, data_to_save,copy_header=True)
    nibabel.nifti1.save(new_img, output_file)

def get_entities(file):
    dir_name = os.path.dirname(file)
    file_name = os.path.basename(file)

    entity={}

    if file is not None and not file == "":
        acquisition = get_bidstag("acq",file)
        if acquisition is not None:
            entity["acquisition"]=acquisition.split("acq-")[1]
            file = file.replace(acquisition, "")

    if file is not None and not file == "":
        modality = get_modality(file)
        if modality is not None:
            entity["modality"]=modality
            file = file.replace(modality, "")
    
    return entity


def get_bidstag(tag,file,all_occurences=False):
    dir_name = os.path.dirname(file)
    file_name = os.path.basename(file)

    tag=list(filter(lambda x: "{}-".format(tag) in x, file_name.split("_")))
    if tag:
        if all_occurences:
            return tag
        else:
            return tag[0]
    else:
        return None

def insert_modality(tag,file):
    dir_name = os.path.dirname(file)
    file_name = os.path.basename(file)
    ind=file_name.index(".")
    file_name = file_name[:ind] + "_" + tag + file_name[ind:] 

    file = os.path.join(dir_name,file_name)  
    return file

def get_modality(file):
    dir_name = os.path.dirname(file)
    file_name = os.path.basename(file)
    noext=file_name.split(".")[0]
    modality=noext.split("_")[-1] 
    return modality


def insert_bidstag(tag,file,overwrite=True):

    dir_name = os.path.dirname(file)
    file_name = os.path.basename(file) 
    file_parts=file_name.split("_")
    
    if len(file_parts) < 2:
        file_name = insert_modality("modality",file_name)
        file_parts=file_name.split("_")


    if not tag in file_parts:
        tag_stump=tag.split("-")
        if tag_stump:
            test_tag=get_bidstag(tag_stump[0],file_name)
            if test_tag is None or overwrite:
                if tag_stump[0] == "sub":
                    if test_tag is not None:
                        subindex=file_parts.index(test_tag)
                        if subindex != 0:
                            file_parts.pop(subindex)
                            file_parts.insert(0,tag)
                        else:
                            file_parts[0]=tag
                    else:
                        file_parts.insert(0,tag)

                elif tag_stump[0] == "ses":
                    if "sub" in file_parts[0]:
                        if test_tag is not None:
                            subindex=file_parts.index(test_tag)
                            if subindex != 1:
                                file_parts.pop(subindex)
                                file_parts.insert(1,tag)
                            else:
                                file_parts[1]=tag
                        else:
                            file_parts.insert(1,tag)
                    else:
                        print("BIDS malformed - 1st part is not sub- but {}".format(file_parts[0]))
                else:
                    if "ses" in file_parts[1]:
                        if test_tag is not None:
                            subindex=file_parts.index(test_tag)
                            if subindex != 2:
                                file_parts.pop(subindex)
                                file_parts.insert(2,tag)
                            else:
                                file_parts[2]=tag
                        else:
                            file_parts.insert(2,tag)
                    else:
                        file_parts.insert(1,tag)

            else:
                print("Tag type {} exists. Select Override True to replace with {}".format(test_tag,tag))

        else:
            print("Tag {} is malformed. '-' is missing with value".format(tag))

    else:
        print("Tag {} already in {}".format(tag,file))

    file_name="_".join(file_parts)
    file = os.path.join(dir_name,file_name)
    return file

def acquire_lock(lock_path):
    
    lock_file = open(lock_path,"w")

    try:
        fcntl.lockf(lock_file,fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except IOError:
        UTLOGGER.debug(f"Could not acquire lock at {lock_path}. Waiting...")
        return None

def release_lock(lock_file):
    try:
        if lock_file:
            lock_file.close()
    except Exception as e:
        UTLOGGER.debug(f"problem closing lockfile {lock_file}.\n{e}")


def getSubjectInfo(labels_dict, participant_label):
    sessions_file = getParams(labels_dict,"SESSIONS_FILE")
    if sessions_file:
        sessions_df = pd.read_table(sessions_file,sep="\t")
        search_df = sessions_df[(sessions_df["bids_participant_id"]=="sub-" + drop_sub(participant_label))]
        if search_df.empty:
            UTLOGGER.info(f"No Subject_ID values found for {participant_label} in {sessions_file}. Returning passed value.")
            return participant_label
        else:
            sub_id=[sub_id for sub_id in list(search_df.xnat_subject_id.values)]
            if not sub_id:
                UTLOGGER.info(f"No Subject_ID values found for {participant_label} in {sessions_file}. Returning passed value.")
                return participant_label
            else:
                return sub_id[0]
    else:
        UTLOGGER.info(f"No Subject_ID values found for {participant_label} in {sessions_file}. Returning passed value.")
        return participant_label   


LOCK_SUFFIX=".lock"
def getSubjectBids(labels_dict,bids_dir,participant_label,xnat_project,user,password):

    lock_path = os.path.join(getParams(labels_dict,"LOCK_DIR"),participant_label + LOCK_SUFFIX)
    lock_file = acquire_lock(lock_path)

    xnat_host = getParams(labels_dict,"XNAT_HOST")

    count = 0
    # 6 minutes timeout - this should be enough!
    TIMEOUT=360
    while not lock_file:
        time.sleep(1)
        count = count + 1
        lock_file = acquire_lock(lock_path)
        # prevent indefinite loop; take our chance on a downstream error.
        if count >= TIMEOUT:
            break

    IN_XNAT =  getParams(labels_dict,"IN_XNAT")
    if IN_XNAT:
        IN_XNAT = isTrue(IN_XNAT)
    else:
        IN_XNAT = True

    try:

        FORCEDOWNLOAD=False
        force_download = getParams(labels_dict,"FORCE_BIDS_DOWNLOAD")
        if force_download and isTrue(force_download):
            FORCEDOWNLOAD=True

        if not os.path.isdir(os.path.join(bids_dir,"sub-"+participant_label)) or FORCEDOWNLOAD:
            UTLOGGER.info(f"BIDS folder for {participant_label} not present.")
            if IN_XNAT:
                command_base, container = getContainer(labels_dict,nodename="process_fsl_glm",SPECIFIC="XNATDOWNLOAD_CONTAINER")

                UTLOGGER.info("Downloading started from XNAT.")
                subject_id = getSubjectInfo(labels_dict,participant_label)
                getSubjectSessionsXNAT(bids_dir,participant_label,"BIDS-AACAZ",xnat_project,xnat_host,user,password,subject_id=subject_id)
            else:
                UTLOGGER.info(f"IN_XNAT set to {IN_XNAT}. Do not have a means of obtaining data for {participant_label}. Please add this subject's data to {bids_dir}")

        else:
            print(f"BIDS folder for {participant_label} already present. No need to retrieve")

    finally:
        release_lock(lock_file)
        try:
            os.remove(lock_path)
        except Exception as e:
            pass

def getSubjectSessionsXNAT(bids_dir,subject_label,resource_label,project,host,user,password,subject_id=None):

    import xnat
    with xnat.connect(server=host,user=user, password=password) as connection:
        project = connection.projects[project]
        if not subject_id:
            subject = project.subjects[subject_label]
        else:
            subject = project.subjects[subject_id]
        experiments = subject.experiments
        expcount = len(experiments)
        for expnum in range(expcount):
            experiment = experiments[expnum]
            if resource_label in experiment.resources:
                resource = experiment.resources[resource_label]
                tmpdir = tempfile.mkstemp()[1] + "_" + subject_label
                if not os.path.exists(tmpdir):
                    os.makedirs(tmpdir,exist_ok=True)
                tmpzip = os.path.join(tmpdir,subject_label + ".zip")
                resource.download(tmpzip)
                shutil.unpack_archive(tmpzip,tmpdir)
                bidspath = glob.glob(os.path.join(tmpdir,f"*/resources/{resource_label}/files/sub*"))
                dataset_desc = glob.glob(os.path.join(tmpdir,f"*/resources/{resource_label}/files/dataset_description.json"))
                if bidspath:
                    bidspath = bidspath[0]
                    bidssubject = bidspath.split("/")[-1]
                    shutil.copytree(bidspath,os.path.join(bids_dir,bidssubject), dirs_exist_ok=True)
                    if dataset_desc:
                        target_dataset_desc =os.path.join(bids_dir,"dataset_description.json")
                        if not os.path.exists(target_dataset_desc):
                            shutil.copy(dataset_desc[0],target_dataset_desc)
                    shutil.rmtree(tmpdir)
                else:
                    UTLOGGER.info(f"Problem dowbloading data for {subject_label} using {resource_label} in {experiment.label}")
                    if subject_id:
                        UTLOGGER.info(f"{subject_id} used as key to access data")




def get_freesurfer_subregionstats(stats_file, prefix="",participant_label="",session_label=""):
    if not prefix is None and not prefix =="":
        prefix=prefix+"_"
    else:
        prefix =""

    with open(stats_file,"r") as in_file:
        lines = in_file.readlines()

    tab_col_index=-2
    tab_val_index=-1
    get_col_index=0


    table_columns = [x.split()[tab_col_index] for x in lines]
    table_columns = [x.replace('\n','') for x in table_columns]
    table_columns = table_columns[get_col_index:]
    table_columns =[ prefix + x  + "_Volume" for x in table_columns]
    table_values = [x.split()[-tab_val_index] for x in lines]
    table_values = table_values[get_col_index:]

    if len(table_columns) > 0 and len(table_values) > 0 and len(table_columns) == len(table_values):
        cum_df = pd.DataFrame([table_values])
        cum_df.columns = table_columns
        if session_label is not None and not session_label == "":
            cum_df.insert(0,"session_id",["ses-"+session_label])
        if participant_label is not None and not participant_label == "":
            cum_df.insert(0,"subject_id",["sub-"+participant_label])
        return cum_df
    else:
        return None

def get_freesurfer_hippostats(stats_file, prefix="",participant_label="", session_label=""):
    if not prefix is None and not prefix =="":
        prefix=prefix+"_"
    else:
        prefix =""

    with open(stats_file,"r") as in_file:
        lines = in_file.readlines()

    table_columns = [x.split(" ")[-1] for x in lines]
    table_columns = [x.replace('\n','') for x in table_columns]
    table_columns = table_columns[1:]
    table_columns =[ prefix + x  + "_Volume" for x in table_columns]
    table_values = [x.split()[-2] for x in lines]
    table_values = table_values[1:]

    if len(table_columns) > 0 and len(table_values) > 0 and len(table_columns) == len(table_values):
        cum_df = pd.DataFrame([table_values])
        cum_df.columns = table_columns
        if session_label is not None and not session_label == "":
            cum_df.insert(0,"session_id",["ses-"+session_label])
        if participant_label is not None and not participant_label == "":
            cum_df.insert(0,"subject_id",["sub-"+participant_label])
        return cum_df
    else:
        return None



def get_freesurfer_genstats(stats_file,columns, prefix="",participant_label="",session_label=""):

    if not prefix is None and not prefix =="":
        prefix=prefix+"_"
    else:
        prefix =""

    column_dict={}
    column_dict["StructName"] = 1
    for column in columns:
        column_dict[column] = 1

    header_list=[]
    value_list=[]

    with open(stats_file,"r") as in_file:
        lines = in_file.readlines()
    for line in lines:
        if line.startswith("# Measure"):
            header = line.split(",")[1].strip()
            header_list.append(prefix+header)
            value = line.split(",")[-2].strip()
            value_list.append(value)
        if line.startswith("# ColHeaders"):
            colheaders=line.split()[2:]
            for itemkey, itemvalue in column_dict.items():
                column_dict[itemkey]=colheaders.index(itemkey)

        if not line.startswith("#"):
            header=line.split()[column_dict["StructName"]]
            for itemkey, itemvalue in column_dict.items():
                if not itemkey == "StructName":
                    header_list.append(prefix + header + "_{}".format(itemkey))
                    value=line.split()[itemvalue]
                    value_list.append(value)
    
    if len(header_list) > 0 and len(value_list) > 0 and len(header_list) == len(value_list):
        cum_df = pd.DataFrame([value_list])
        cum_df.columns = header_list
        if session_label is not None and not session_label == "":
            cum_df.insert(0,"session_id",["ses-"+session_label])
        if participant_label is not None and not participant_label == "":
            cum_df.insert(0,"subject_id",["sub-"+participant_label])
        return cum_df
    else:
        return None

def recurse_dict(jsondict,itemkeyorig, retdict):
    for itemkey, itemvalue in jsondict.items():
        if isinstance(itemvalue,dict):
            retdict = recurse_dict(itemvalue, itemkeyorig + "." + itemkey,retdict)
        else:
            retdict[itemkeyorig + "." + itemkey]=itemvalue
    return retdict


def get_flatdict(jsondata):
    flatdict=OrderedDict()

    for itemkey, itemvalue in jsondata.items():
        retdict=OrderedDict()
        if isinstance(itemvalue,dict):
            retdict = recurse_dict(itemvalue,itemkey,retdict)
        else:
            newitemkey=itemkey
            newitemvalue=itemvalue
            retdict[newitemkey]=newitemvalue

        for retitemkey, retitemvalue in retdict.items():
            if isinstance(retitemvalue,list):
                retitemvalue = [str(x) for x in retitemvalue]
                retitemvalue = " ".join(retitemvalue)
            flatdict[retitemkey]=retitemvalue

    return flatdict


def get_text(text_file, extract_columns=None, prefix="",participant_label="", session_label="",delimiter='\s+'):
    if not prefix is None and not prefix =="":
        prefix=prefix+"."
    else:
        prefix =""

    try:
        df = pd.read_csv(text_file,sep=delimiter,header=None)
    except Exception as jde:
        df=pd.DataFrame()

    if not df.empty:
        all_columns = {}
        all_columns = df.columns.to_list()

        table_columns = []
        table_values = []
        if not extract_columns:
            extract_columns = all_columns

        for index in range(len(extract_columns)):
            if index < len(all_columns):
                table_columns.append(extract_columns[index])
                table_values.append(df[index].iloc[0])
            else:
                UTLOGGER.warn(f"Index {index} greater than length of columns in {text_file} - skipping")

        if len(table_columns) > 0:
            table_columns = [prefix+x for x in table_columns]

        if len(table_columns) > 0 and len(table_values) > 0 and len(table_columns) == len(table_values):
            cum_df = pd.DataFrame([table_values])
            cum_df.columns = table_columns
            if session_label is not None and not session_label == "":
                cum_df.insert(0,"session_id",["ses-"+session_label])
            if participant_label is not None and not participant_label == "":
                cum_df.insert(0,"subject_id",["sub-"+participant_label])
            return cum_df
        else:
            return None   


def get_csvstats(csv_file, extract_columns=None, prefix="",participant_label="", session_label="",delimiter=","):
    if not prefix is None and not prefix =="":
        prefix=prefix+"."
    else:
        prefix =""

    try:
        df = pd.read_table(csv_file,sep=delimiter)
    except Exception as jde:
        df=pd.DataFrame()

    if not df.empty:
        all_columns = {}
        all_columns = df.columns.to_list()

        table_columns = []
        table_values = []
        if not extract_columns:
            extract_columns = all_columns

        for column in extract_columns:
            if column in all_columns:
                table_columns.append(column)
                table_values.append(df[column].iloc[0])
            else:
                UTLOGGER.warn(f"Column {column} not defined in {csv_file} - skipping")

        if len(table_columns) > 0:
            table_columns = [prefix+x for x in table_columns]

        if len(table_columns) > 0 and len(table_values) > 0 and len(table_columns) == len(table_values):
            cum_df = pd.DataFrame([table_values])
            cum_df.columns = table_columns
            if session_label is not None and not session_label == "":
                cum_df.insert(0,"session_id",["ses-"+session_label])
            if participant_label is not None and not participant_label == "":
                cum_df.insert(0,"subject_id",["sub-"+participant_label])
            return cum_df
        else:
            return None


def get_jsonstats(json_file, extract_columns=None, prefix="",participant_label="", session_label=""):
    if not prefix is None and not prefix =="":
        prefix=prefix+"."
    else:
        prefix =""

    try:
        with open(json_file,"r") as in_file:
            jsondata = json.load(in_file)
    except json.decoder.JSONDecodeError as jde:
        jsondata=None

    all_columns = {}
    if jsondata:
        all_columns = get_flatdict(jsondata)

    table_columns = []
    table_values = []
    if not extract_columns:
        table_columns = all_columns.keys()
        table_values = all_columns.values()
    else:

        for column in extract_columns:
            if column in all_columns.keys():
                table_columns.append(column)
                table_values.append(all_columns[column])
            else:
                UTLOGGER.warn(f"Column {column} not defined in {json_file} - skipping")

    if len(table_columns) > 0:
        table_columns = [prefix+x for x in table_columns]

    if len(table_columns) > 0 and len(table_values) > 0 and len(table_columns) == len(table_values):
        cum_df = pd.DataFrame([table_values])
        cum_df.columns = table_columns
        if session_label is not None and not session_label == "":
            cum_df.insert(0,"session_id",["ses-"+session_label])
        if participant_label is not None and not participant_label == "":
            cum_df.insert(0,"subject_id",["sub-"+participant_label])
        return cum_df
    else:
        return None

def isTrue(arg):
    return arg is not None and (arg == 'Y' or arg == '1' or arg == 'True' or arg == 'true')


def get_value_bytype(vartype,varstring):
    varvalue = None
    if vartype is not None and varstring is not None:
        if vartype  == 'text':
            varvalue=str(varstring)
        elif vartype  == 'float':
            varvalue=float(str(varstring))
        elif vartype  == 'integer':
            varvalue=int(str(varstring))
        elif vartype  == 'boolean':
            varvalue=isTrue(str(varstring))
        elif vartype  == 'list':
            if str(varstring).startswith("[") and str(varstring).endswith("]"):
                varvalue=eval(str(varstring))
        elif vartype  == 'dict':
            if str(varstring).startswith("{") and str(varstring).endswith("}"):
                varvalue=eval(str(varstring))
        else:
            varvalue=str(varstring)

    return varvalue

def create_array(participants, participants_file, projects_list = None, sessions_list=None, sessions_file = None, LOGGER=UTLOGGER):
    if sessions_file is not None:
        df = pd.read_table(sessions_file,sep="\t")
    else:
        df = pd.read_table(participants_file,sep="\t")

    array=[]
    if participants is not None and len(participants) > 0 and sessions_list and projects_list and sessions_file:
        for part_count in range(len(participants)):
            array_index = df.loc[(df["bids_participant_id"] == "sub-" + drop_sub(participants[part_count])) & (df["project"] == projects_list[part_count]) & (df["bids_session_id"].str.contains(sessions_list[part_count]))].index.values[0] + 1
            array.append(str(array_index))
        array.sort()
        return  ",".join(array)
    elif participants is not None and len(participants) > 0:
        for participant in participants:
            try:
                array.append(str(df[df["bids_participant_id"]== "sub" + drop_sub(participant)].index.values[0] + 1))
            except Exception as exp:
                UTLOGGER.debug(f"problem finding participant: {participant}")

        array.sort()
        return  ",".join(array)
    else:
        return "1:" + str(len(df))

def get_projectmap(participants, participants_file,session_labels=[],sessions_file = None, subject_exclusions=[]):

    if participants_file is not None:
        df = pd.read_table(participants_file,sep="\t")
    else:
        df = pd.read_table(sessions_file,sep="\t")

    if len(participants) == 1 and participants[0]=="ALL_SUBJECTS":
        participants = df["bids_participant_id"].tolist()

    # process exclusions
    participants = list(set(participants).difference(set(subject_exclusions)))

    # sessions are defined and so we will use this as priority
    project_list=[]
    shared_project_list=[]
    participant_list=[]
    sessions_list=[]
    if sessions_file is not None and session_labels:
        sessions_df = pd.read_table(sessions_file,sep="\t")
        # participants and sessions are defined
        if participants is not None and len(participants) > 0:
            for participant in participants:
                if session_labels[0]=="ALL_SESSIONS":
                    search_df = sessions_df[(sessions_df["bids_participant_id"]=="sub-" + drop_sub(participant))]
                    ses=[drop_ses(ses) for ses in list(search_df.bids_session_id.values)]
                    sessions_list.extend(ses)
                    sub=[drop_sub(sub) for sub in list(search_df.bids_participant_id.values)]
                    participant_list.extend(sub)
                    proj=[proj for proj in list(search_df.project.values)]
                    project_list.extend(proj)
                    if 'shared_projects' in df.columns:
                        shared_proj=[shared_proj for shared_proj in list(search_df.shared_projects.values)]
                        shared_project_list.extend(shared_proj)
                else: 
                    for session_label in session_labels:
                        search_df = sessions_df[(sessions_df["bids_participant_id"]=="sub-" + drop_sub(participant)) & (sessions_df["bids_session_id"].str.contains(session_label))]
                        if search_df.empty:
                            UTLOGGER.info(f"No values found for {participant} and {session_label} in {sessions_file}")
                        else:
                            ses=[drop_ses(ses) for ses in list(search_df.bids_session_id.values)]
                            sessions_list.extend(ses)
                            sub=[drop_sub(sub) for sub in list(search_df.bids_participant_id.values)]
                            participant_list.extend(sub)
                            proj=[proj for proj in list(search_df.project.values)]
                            project_list.extend(proj)
                            if 'shared_projects' in df.columns:
                                shared_proj=[shared_proj for shared_proj in list(search_df.shared_projects.values)]
                                shared_project_list.extend(shared_proj)
        else:
            UTLOGGER.info(f"Cannot process pipelines. No participants have been specified")
    else:
        if participants is not None and len(participants) > 0:
            for participant in participants:
                project_list.append(str(df[df["bids_participant_id"]==participant].project.values[0]))
                if 'shared_projects' in df.columns:
                    shared_project_list.append(str(df[df["bids_participant_id"]==participant].shared_projects.values[0]))
                                
            sessions_list=[None for proj in project_list]
        else:
            UTLOGGER.info(f"Cannot process pipelines. No participants have been specified")

    return  [ participant_list, project_list, sessions_list, shared_project_list ]


def create_script(header,template,panpipe_labels, script_file, LOGGER=UTLOGGER):
    with open(header,"r") as infile:
        headerlines=infile.readlines()

    with open(template,"r") as infile:
        templatelines = infile.readlines()

    newscript=[]
    header = "".join(headerlines)
    header = header + "\n\n"
    newscript.append(header)

    for templateline in templatelines:
        newscript.append(substitute_labels(templateline, panpipe_labels))

    with open(script_file,"w") as outfile:
        outfile.writelines(newscript)


def getDependencies(job_ids,panpipe_labels,LOGGER=UTLOGGER):

    slurm_dependency = getParams(panpipe_labels,"SLURM_DEPENDENCY")
    if not slurm_dependency:
        slurm_dependency="afterany"


    dependency_string=""
    pipeline_dependency = getParams(panpipe_labels,"DEPENDENCY")
    if pipeline_dependency is not None:
        if isinstance(pipeline_dependency,list):
            job_ids_string=""
            for pipe_dep in pipeline_dependency:
                if pipe_dep in job_ids.keys():
                    job_id = job_ids[pipe_dep]
                    if job_id is not None:
                        job_ids_string=job_ids_string + ":" + job_id
                    
            if not job_ids_string == "":
                dependency_string = f"--dependency={slurm_dependency}{job_ids_string}"               


        else:
            if pipeline_dependency in job_ids.keys():
                job_id = job_ids[pipeline_dependency]
                if job_id is not None:
                    dependency_string = f"--dependency={slurm_dependency}:{job_id}"

    return dependency_string



def submit_script(participants, participants_file, pipeline, panpipe_labels,job_ids, analysis_level,projects_list = None, sessions_list=None, sessions_file = None, LOGGER=UTLOGGER, script_dir=None, panlabel=None):
    headerfile=getParams(panpipe_labels,"SLURM_HEADER")
    templatefile=getParams(panpipe_labels,"SLURM_TEMPLATE")
    if not panlabel:
        panlabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") 

    script_base=pipeline + "_" + panlabel
   
    if script_dir is None:
        script_dir=os.path.join(getParams(panpipe_labels,"SLURM_SCRIPT_DIR"),script_base)

    if not os.path.exists(script_dir):
        os.makedirs(script_dir)
    script_file = os.path.join(script_dir,script_base + '.pbs')
    labels_file = os.path.join(script_dir,script_base + '.config')
    updateParams(panpipe_labels, "RUNTIME_CONFIG_FILE", labels_file)

    create_script(headerfile,templatefile,panpipe_labels, script_file)
    updateParams(panpipe_labels, "PIPELINE_SCRIPT", script_file)
    dependencies = getDependencies(job_ids,panpipe_labels)

    if LOGGER:
        LOGGER.info(f"Runtime Config file created: {labels_file}")
        LOGGER.info(f"Pipeline Script file created: {script_file}")
    
    if analysis_level == "participant":

        outlog =f"log-%a_{pipeline}_{panlabel}.panout"
        jobname = f"{pipeline}_pan_ss"

        array = create_array(participants, participants_file,projects_list = projects_list, sessions_list=sessions_list, sessions_file = sessions_file)
        
        command = "sbatch"\
        " --job-name " + jobname +\
        " --output " + outlog + \
        " --array=" + array + \
        " " + dependencies + \
        " " + script_file
    else:
        outlog =f"log-group_{pipeline}_{panlabel}.panout"
        jobname = f"{pipeline}_pan_grp"

        command = "sbatch"\
        " --job-name " + jobname +\
        " --output " + outlog + \
        " " + dependencies + \
        " " + script_file        
    
    evaluated_command = substitute_labels(command,panpipe_labels)
    if LOGGER:
        LOGGER.info(evaluated_command)

    updateParams(panpipe_labels, "SLURM_COMMAND", evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)

    # A bit of a hack - these labels in labels_dict prevent nupype from caching properly as they always change, so remove before saving
    removeParam(panpipe_labels, "RUNTIME_CONFIG_FILE")
    removeParam(panpipe_labels, "PIPELINE_SCRIPT")

    export_labels(panpipe_labels,labels_file)

    CURRDIR=os.getcwd()
    os.chdir(script_dir)

    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)

    if LOGGER:
        LOGGER.info(results.stdout)
    else:
        print(results.stdout)
 
    os.chdir(CURRDIR)

    return results.stdout.split()[3]

def getGlob(globstring,multiple=False,default_result=""):
    if globstring:
        if "*" in globstring:
            glob_results = glob.glob(globstring)
            if not multiple:
                return getFirstFromList(glob_results,default_result)
            else:
                return glob_results
        else:
            return globstring
    else:
        return default_result

def getFirstFromList(itemlist,default_result=""):
    if len (itemlist) > 0:
        return(itemlist[0])
    else:
        return default_result

def newfile(outputdir=None, assocfile=None, prefix=None, suffix=None, intwix=None, extension=None, replace=False):
   
    if assocfile is None:
        assocfile = tempfile.mkstemp()[1]
        filename=os.path.basename(assocfile)
    else:
        filename=os.path.basename(os.path.abspath(assocfile))
        
    if outputdir is None:
        outputdir = os.path.dirname(os.path.abspath(assocfile))
    else:
        outputdir = os.path.abspath(outputdir)
    
    if not prefix is None:
        if not replace:
            filename=prefix + "_" + filename
        else:
            fileparts = filename.split("_")
            if len(fileparts) > 1:
                fileparts[0]=prefix
                filename = "_".join(fileparts)
            else:
                filename=prefix + "_" + filename

    if not extension is None:
        fileparts = filename.split(".")
        basename = fileparts[0]
        if not extension[0] == ".":
            extension="." + extension
        filename = basename + extension        
        
    if not suffix is None:
        fileparts = filename.split(".")
        basename = fileparts[0]
        extension = ".".join(fileparts[1:])
        if len(extension) > 0:
            if not extension[0] == ".":
                extension="." + extension
        if not replace:
            filename = basename + "_" + suffix + extension
        else:
            fileparts = basename.split("_")
            if len(fileparts) > 1:
                fileparts[-1]=suffix
                basename = "_".join(fileparts)
                filename = basename + extension
            else:
                filename = basename + "_"+ suffix + extension

    if not intwix is None:
        filename = "_".join(filename.split("_")[0:-1] + [intwix] + [filename.split("_")[-1]])


                
    return os.path.join(outputdir,filename)
        
def getTransName(fromfile, tofile):
    if fromfile is not None and tofile is not None:
        return "from-" + os.path.basename(fromfile).split(".")[0] + "_" + "to-" + os.path.basename(tofile).split(".")[0]
        
def getProcNums(panpipe_labels):

    procnum_list=[mp.cpu_count()]

    try:
        pipeline_count = int(getParams(panpipe_labels,"PIPELINE_THREADS"))
        procnum_list.append(pipeline_count)
    except ValueError as ve:
        pass
    except TypeError as te:
        pass
    

    try:
        ENV_PROCS = getParams(panpipe_labels,"ENV_PROCS")
        if ENV_PROCS is not None and ENV_PROCS in os.environ.keys():
            env_count = int(os.environ[ENV_PROCS])
            procnum_list.append(env_count)
    except ValueError as ve:
        pass
    except TypeError as te:
        pass
    
    return int(np.min(np.array(procnum_list)))


def add_mask_roi(atlas_file, roi_in, panpipe_labels, high_thresh=None,prob_thresh=0.5,roi_transform=None,invert_roi=False):

    workdir = os.path.join(os.path.dirname(atlas_file),'roi_temp')
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    trans_workdir = os.path.join(os.path.dirname(atlas_file),'roi_transformed')
    if not os.path.isdir(trans_workdir):
        os.makedirs(trans_workdir)

    if prob_thresh:
        PROBTHRESH=f" -thr {prob_thresh}"
    else:
        PROBTHRESH=""

    if high_thresh:
        HIGHTHRESH=f" -uthr {high_thresh}"
    else:
        HIGHTHRESH = ""

    if invert_roi:
        BINSTRING = " -binv"
    else:
        BINSTRING = " -bin"


    # store roi in work dir for
    command_base, container = getContainer(panpipe_labels,nodename="add_atlas_roi",SPECIFIC="NEURO_CONTAINER")
    new_roi=newfile(trans_workdir, roi_in, suffix="desc-label")
    command = f"{command_base} fslmaths"\
        f"  {roi_in}" +\
        HIGHTHRESH +\
        PROBTHRESH +\
        BINSTRING +\
        f" {new_roi}" 
    
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    from panpipelines.nodes.antstransform import antstransform_proc

    roi_transform_ref = getParams(panpipe_labels,"ROI_TRANSFORM_REF")
    if roi_transform:
        CURRDIR = os.getcwd()
        os.chdir(trans_workdir)
        results = antstransform_proc(panpipe_labels, new_roi,roi_transform, roi_transform_ref)
        new_roi_transformed = results['out_file']
        os.chdir(CURRDIR)
    else:
        new_roi_transformed = newfile(trans_workdir, new_roi)
        shutil.move(new_roi, new_roi_transformed)

    # make output file into int. This was initially don in ANTS above but had issues with rois that had value of 1
    command = f"{command_base} fslmaths"\
            f"  {new_roi_transformed}"\
            f" {new_roi_transformed}" \
             " -odt int"
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    if os.path.exists(atlas_file):
        command = f"{command_base} fslmaths"\
            f"  {new_roi_transformed}"\
            f" -mas {atlas_file}" +\
            f" {atlas_file}"
    else:
        command = f"{command_base} fslmaths"\
            f" {new_roi_transformed}"\
            f" {atlas_file}" 
    
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)


def add_atlas_roi(atlas_file, roi_in, roi_value, panpipe_labels, high_thresh=None,low_thresh=None,prob_thresh=0.5,roi_transform=None):

    workdir = os.path.join(os.path.dirname(atlas_file),'roi_temp')
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    trans_workdir = os.path.join(os.path.dirname(atlas_file),'roi_transformed')
    if not os.path.isdir(trans_workdir):
        os.makedirs(trans_workdir)

    if prob_thresh:
        PROBTHRESH=f" -thr {prob_thresh}"
    else:
        PROBTHRESH=""

    if high_thresh:
        HIGHTHRESH=f" -uthr {high_thresh}"
    else:
        HIGHTHRESH = ""

    if low_thresh:
        LOWTHRESH=f" -thr {low_thresh}"
    else:
        LOWTHRESH=""

    # store roi in work dir for
    command_base, container = getContainer(panpipe_labels,nodename="add_atlas_roi",SPECIFIC="NEURO_CONTAINER")
    new_roi=newfile(trans_workdir, roi_in, suffix="desc-label")
    command = f"{command_base} fslmaths"\
        f"  {roi_in}" +\
        PROBTHRESH +\
        " -bin "\
        f" -mul {roi_value}" \
        f" {new_roi}" 
    
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    from panpipelines.nodes.antstransform import antstransform_proc

    roi_transform_ref = getParams(panpipe_labels,"ROI_TRANSFORM_REF")
    if roi_transform:
        CURRDIR = os.getcwd()
        os.chdir(trans_workdir)
        results = antstransform_proc(panpipe_labels, new_roi,roi_transform, roi_transform_ref)
        new_roi_transformed = results['out_file']
        os.chdir(CURRDIR)
    else:
        new_roi_transformed = newfile(trans_workdir, new_roi)
        shutil.move(new_roi, new_roi_transformed)

    # make output file into int. This was initially don in ANTS above but had issues with rois that had value of 1
    command = f"{command_base} fslmaths"\
            f"  {new_roi_transformed}"\
            f" {new_roi_transformed}" \
             " -odt int"
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    if os.path.exists(atlas_file):
        command = f"{command_base} fslmaths"\
            f"  {new_roi_transformed}"\
            f" -add {atlas_file}" +\
            LOWTHRESH +\
            HIGHTHRESH +\
            f" {atlas_file}"
    else:
        command = f"{command_base} fslmaths"\
            f" {new_roi_transformed}"\
            f" {atlas_file}" 
    
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)


def create_3d_atlas_from_rois(atlas_file, roi_list,panpipe_labels, roi_values=None,prob_thresh=0.5,explode3d=True):

    roi_list = expand_rois(roi_list,os.path.dirname(atlas_file),panpipe_labels,explode3d=explode3d)
    roi_transform_mat = getParams(panpipe_labels,"ROI_TRANSFORM_MAT")
    panpipe_labels=updateParams(panpipe_labels,"ROI_TRANSFORM_REF",getParams(panpipe_labels,"NEWATLAS_TRANSFORM_REF"))

    numrois=len(roi_list)
    if roi_values is None:
        roi_values=range(1,numrois+1)

    # create rois
    for roi_num in range(numrois):
        roi = roi_list[roi_num]
        roi_transform=None
        if roi_transform_mat and roi_num < len(roi_transform_mat):
            roi_transform = roi_transform_mat[roi_num]
        roi_value = roi_values[roi_num]
        if isinstance(prob_thresh,list):
            prob_thresh_val = float(prob_thresh[np.min((roi_num,len(prob_thresh)-1))])
        elif prob_thresh:
            prob_thresh_val = prob_thresh
        else:
            prob_thresh_val = ""

        add_atlas_roi(atlas_file, roi, roi_value, panpipe_labels,high_thresh=roi_value,prob_thresh=prob_thresh_val,roi_transform=roi_transform)

    return atlas_file

def create_3d_mask_from_rois(atlas_file, roi_list,panpipe_labels, roi_values=None,prob_thresh=0.5,explode3d=True,invert_roi=False):

    roi_list = expand_rois(roi_list,os.path.dirname(atlas_file),panpipe_labels,explode3d=explode3d)
    roi_transform_mat = getParams(panpipe_labels,"ROI_TRANSFORM_MAT")
    panpipe_labels=updateParams(panpipe_labels,"ROI_TRANSFORM_REF",getParams(panpipe_labels,"NEWATLAS_TRANSFORM_REF"))

    numrois=len(roi_list)

    # create rois
    for roi_num in range(numrois):
        roi = roi_list[roi_num]
        roi_transform=None
        if roi_transform_mat and roi_num < len(roi_transform_mat):
            roi_transform = roi_transform_mat[roi_num]

        if isinstance(roi_values,list):
            roi_value = float(roi_values[np.min((roi_num,len(roi_values)-1))])
        elif prob_thresh:
            roi_value = roi_values
        else:
            roi_value = None

        if isinstance(prob_thresh,list):
            prob_thresh_val = float(prob_thresh[np.min((roi_num,len(prob_thresh)-1))])
        elif prob_thresh:
            prob_thresh_val = prob_thresh
        else:
            prob_thresh_val = 0.5

        if isinstance(invert_roi,list):
            invert_roi_val = isTrue(invert_roi[np.min((roi_num,len(invert_roi)-1))])
        elif invert_roi:
            invert_roi_val = invert_roi
        else:
            invert_roi_val = False

        add_mask_roi(atlas_file, roi, panpipe_labels,high_thresh=roi_value,prob_thresh=prob_thresh_val,roi_transform=roi_transform,invert_roi=invert_roi_val)

    return atlas_file

def merge_atlas_roi(atlas_file, roi_list, panpipe_labels, high_thresh=None,low_thresh=None):

    workdir = os.path.join(os.path.dirname(atlas_file),'roi_temp')
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    trans_workdir = os.path.join(os.path.dirname(atlas_file),'roi_transformed')
    if not os.path.isdir(trans_workdir):
        os.makedirs(trans_workdir)

    if high_thresh:
        HIGHTHRESH=f" -uthr {high_thresh}"
    else:
        HIGHTHRESH = ""

    command_base, container = getContainer(panpipe_labels,nodename="merge_atlas_roi",SPECIFIC="NEURO_CONTAINER")

    roicount=0
    numrois=len(roi_list)
    roi_files=[]
    for roi_in in roi_list:       
        # store roi in work dir\
        if isinstance(low_thresh,list):
            low_thresh_val = float(low_thresh[np.min((roicount,len(low_thresh)-1))])
        elif low_thresh:
            low_thresh_val = low_thresh
        else:
            low_thresh_val = ""

        if low_thresh_val:
            LOWTHRESH=f" -thr {low_thresh_val}"
        else:
            LOWTHRESH=""
        
        new_roi=newfile(workdir, roi_in,suffix="desc-bin")
        command = f"{command_base} fslmaths"\
            f"  {roi_in}" +\
            LOWTHRESH +\
            HIGHTHRESH +\
            " -bin "\
            f" {new_roi}"
        evaluated_command=substitute_labels(command,panpipe_labels)
        results = runCommand(evaluated_command)
        roi_files.append(new_roi)
        roicount=roicount+1

    from panpipelines.nodes.antstransform import antstransform_proc
    roi_files_transformed=[]
    roi_transform_mat = getParams(panpipe_labels,"ROI_TRANSFORM_MAT")
    roi_transform_ref = getParams(panpipe_labels,"ROI_TRANSFORM_REF")
    for roi_num in range(len(roi_files)):
        if roi_transform_mat and roi_num < len(roi_transform_mat):
            roi_file=roi_files[roi_num]
            roi_transform = roi_transform_mat[roi_num]
            CURRDIR=os.getcwd()
            os.chdir(trans_workdir)
            results = antstransform_proc(panpipe_labels, roi_file,roi_transform, roi_transform_ref)
            os.chdir(CURRDIR)
            new_roi_transform_file=results['out_file']
        else:
            new_roi_transform_file= newfile(trans_workdir, new_roi)
            shutil.move(roi_files[roi_num], new_roi_transform_file)
        # make output file into int. This was initially don in ANTS above but had issues with rois that had value of 1
        command = f"{command_base} fslmaths"\
                f"  {new_roi_transform_file}"\
                f" {new_roi_transform_file}" \
                " -odt int"
        evaluated_command=substitute_labels(command,panpipe_labels)
        results = runCommand(evaluated_command)
        roi_files_transformed.append(new_roi_transform_file)
        
    if roi_files_transformed:
        roi_string=" ".join(roi_files_transformed)
        command = f"{command_base} fslmerge"\
            " -t" \
            f" {atlas_file}" +\
            " " + roi_string

        evaluated_command=substitute_labels(command,panpipe_labels)
        results = runCommand(evaluated_command)

    return atlas_file

def create_4d_atlas_from_rois(atlas_file, roi_list,panpipe_labels, roi_values=None, high_thresh=None, low_thresh=0.5,explode3d=True):

    panpipe_labels=updateParams(panpipe_labels,"ROI_TRANSFORM_REF",getParams(panpipe_labels,"NEWATLAS_TRANSFORM_REF"))
    roi_list = expand_rois(roi_list,os.path.dirname(atlas_file),panpipe_labels,explode3d=explode3d)
    merge_atlas_roi(atlas_file, roi_list, panpipe_labels,high_thresh=high_thresh, low_thresh=low_thresh)

    return atlas_file


def expand_rois(roi_list, out_dir, panpipe_labels,explode3d=True):
    """ Given a list of roi images with associated transforms, attempt to reconcile a mix of 3D and 4D images in the list such that
        each element in the list is a 3D roi which can be eventually merged into 1 single 3D atlas or 1 single 4D atlas.
    
    Parameters:
    -----------
    roi_list : The list of rois
    out_dir  : Output directory to store temporary files
    panpipe_labels    : Dictionary of config labels. This should contain NEURO_CONTAINER reference to singularity image
    explode3D : bool , default True. Set this to true when you want to treat each roi as a contiguous uniform label regardless of if it is not.
    
    return:
    -------
    Reference to Dictionary is returned
    """
    workdir = os.path.join(out_dir,'roi_list_temp')
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    roi_transform_list=[]
    newatlas_transform = getParams(panpipe_labels,"NEWATLAS_TRANSFORM_MAT")
    new_roi_list = []
    roi_count = 0

    command_base, container = getContainer(panpipe_labels,nodename="expand_rois",SPECIFIC="NEURO_CONTAINER")
    for roi in roi_list:

        # using fsl for manipulations, so convert freesurfer files to nifti
        if Path(roi).suffix == ".mgz":

            mgzdir = os.path.join(out_dir,'roi_mgz_temp')
            if not os.path.isdir(mgzdir):
                os.makedirs(mgzdir)
            fs_command_base, fscontainer = getContainer(panpipe_labels,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER")
            roi_nii = newfile(mgzdir,roi,extension=".nii.gz")
            convMGZ2NII(roi, roi_nii, fs_command_base)
            roi = roi_nii

        roi_transform = None
        if newatlas_transform and roi_count < len(newatlas_transform):
            roi_transform = newatlas_transform[roi_count]

        roi_count = roi_count + 1
        roi_img  = nib.load(roi)
        roi_shape = roi_img.header.get_data_shape()
        if len(roi_shape) > 3:
            for vol in range(len(roi_shape[3])):
                sub_roi_num=vol + 1
                new_roi=newfile(workdir,roi, prefix=f"{roi_count:0>5}_{sub_roi_num:0>5}",suffix="desc-roi")
                command = f"{command_base} fslroi"\
                    f"  {roi}" \
                    f" {new_roi}" \
                    f" {vol}" \
                    " 1" 
                evaluated_command=substitute_labels(command,panpipe_labels)
                results = runCommand(evaluated_command)
                new_roi_list.append(new_roi)
                if roi_transform:
                    roi_transform_list.append(roi_transform)

        else:
            if explode3d:
                atlas_dict,atlas_list=get_avail_labels(roi)
                for thresh in atlas_list:
                    new_roi=newfile(workdir,roi, prefix=f"{roi_count:0>5}_{thresh:0>5}",suffix="desc-roi")
                    command = f"{command_base} fslmaths"\
                        f" {roi}" \
                        f" -thr {thresh}" \
                        f" -uthr {thresh}" \
                        " -bin "\
                        f" {new_roi}"
                    evaluated_command=substitute_labels(command,panpipe_labels)
                    results = runCommand(evaluated_command)
                    new_roi_list.append(new_roi)
                    if roi_transform:
                        roi_transform_list.append(roi_transform)
          
            else:
                new_roi=newfile(workdir,roi, prefix=f"{roi_count:0>5}",suffix="desc-roi")
                command = "cp"\
                " " + roi +\
                " " + new_roi
                evaluated_command=substitute_labels(command,panpipe_labels)
                results = runCommand(evaluated_command)
                new_roi_list.append(new_roi)
                if roi_transform:
                        roi_transform_list.append(roi_transform)

    if roi_transform_list:
        updateParams(panpipe_labels,"ROI_TRANSFORM_MAT",roi_transform_list)
    
    return new_roi_list

def get_avail_labels(atlas_file):
    atlas_dict={}
    atlas_img = nib.load(atlas_file)
    atlas_data = atlas_img.get_fdata()
    max_roi_num = int(np.max(atlas_data))
    for roi_num in range(1,max_roi_num+1):
        num_voxels=np.count_nonzero(atlas_data == roi_num)
        if num_voxels:
            atlas_dict[roi_num]=num_voxels

    atlas_index_list=[]
    atlas_key_list=list(atlas_dict.keys())
    atlas_key_list.sort()
    for atlas_key in atlas_key_list:
        atlas_index_list.append(atlas_key)
    
    return atlas_dict,atlas_index_list


def get_freesurferatlas_index_mode(atlas_file,lutfile,atlas_index,atlas_index_mode=None):
    
    if atlas_index_mode and "freesurf_tsv_general" in atlas_index_mode:
        atlas_index_type="tsv"
        if "contig" in atlas_index_mode:
            atlas_index_type = "tsv_contig"
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=True,use_atlas_max=True,atlas_index_type=atlas_index_type)
    elif atlas_index_mode and "freesurf_general" in atlas_index_mode:
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=False,use_atlas_max=True)
    elif atlas_index_mode and "freesurf_contig_general" in atlas_index_mode:
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=True,use_atlas_max=True)
    elif atlas_index_mode and "hcpmmp1aseg_tsv" in atlas_index_mode:
        atlas_index_type="tsv"
        if "contig" in atlas_index_mode:
            atlas_index_type = "tsv_contig"
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=False,use_atlas_max=False,atlas_index_type=atlas_index_type)
    elif atlas_index_mode and "hcpmmp1aseg" in atlas_index_mode:
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=False,use_atlas_max=False)
    else:
        atlas_dict,atlas_index_out=get_freesurferatlas_index(atlas_file,lutfile,atlas_index,atlas_index_mode=atlas_index_mode)

    return atlas_dict,atlas_index_out


def get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=False,use_atlas_max=True, atlas_index_type=None):
    with open(lutfile,'r') as infile:
        lutlines=infile.readlines()

    lut_dict={}
    lut_max = 0
    for lut_line in lutlines:
        lut_list = lut_line.split()
        if lut_list and lut_list[0].isdigit():           
            lut_roinum = int(lut_list[0])
            lut_max=max(lut_max,lut_roinum)
            lut_roiname = lut_list[1]
            lut_rgba = ",".join(lut_list[2:])
            lut_dict[lut_roinum] = {}
            lut_dict[lut_roinum]["LabelName"]=lut_roiname
            lut_dict[lut_roinum]["RGBA"]=lut_rgba

    atlas_dict={}
    atlas_img = nib.load(atlas_file)
    atlas_data = atlas_img.get_fdata()
    if use_atlas_max:
        max_roi_num = int(np.max(atlas_data))
    else:
        max_roi_num = lut_max 
    for roi_num in range(1,max_roi_num+1):
        num_voxels=np.count_nonzero(atlas_data == roi_num)
        if avail_only:
            if num_voxels:
                atlas_dict[roi_num]=lut_dict[roi_num]
                atlas_dict[roi_num]["Voxels"]=num_voxels
        else:
            if roi_num in lut_dict.keys():
                atlas_dict[roi_num]=lut_dict[roi_num]
            else:
                atlas_dict[roi_num]={}
                atlas_dict[roi_num]["LabelName"]=f"UNK_{roi_num}"
                atlas_dict[roi_num]["RGBA"]="0,0,0,0"
            atlas_dict[roi_num]["Voxels"]=num_voxels

    atlas_index_list=[]
    atlas_key_list=list(atlas_dict.keys())
    atlas_key_list.sort()

    if atlas_index_type and "tsv" in atlas_index_type:
        atlas_index_list.append("index\tlabel")
        contignum=1
        for atlas_key in atlas_key_list:
            if "contig" in atlas_index_type:
                atlas_index_list.append(str(contignum) + "\t" + atlas_dict[atlas_key]["LabelName"])
            else:
                atlas_index_list.append(str(atlas_key) + "\t" + atlas_dict[atlas_key]["LabelName"])
            contignum=contignum+1
    else:
        for atlas_key in atlas_key_list:
            atlas_index_list.append(atlas_dict[atlas_key]["LabelName"])
        
    atlas_index_out = "\n".join(atlas_index_list)
    if atlas_index:
        with open(atlas_index,"w") as outfile:
            outfile.write(atlas_index_out)

    return atlas_dict,atlas_index_out

            
def create_3d_hcpmmp1_aseg(atlas_file,roi_list,panpipe_labels):
    out_dir = os.path.dirname(atlas_file)
    workdir = os.path.join(out_dir,"hcpmmp1_workdir")
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    command_base, container = getContainer(panpipe_labels,nodename="create_3d_hcppmmp1_aseg",SPECIFIC="NEURO_CONTAINER")

    atlas_dir = getParams(panpipe_labels,"ATLAS_DIR")
    SUB=f"sub-{getParams(panpipe_labels,'PARTICIPANT_LABEL')}"
    freesurfer_dir = getParams(panpipe_labels,"FREESURFER_DIR")
    freesurfer_home = getParams(panpipe_labels,"FREESURFER_HOME")
    if not freesurfer_home:
        freesurfer_home = "/opt/freesurfer"

    lh_hcpannot = os.path.join(atlas_dir, "lh.HCP-MMP1.annot")
    lh_hcpannot_trg = os.path.join(freesurfer_dir,SUB,"label","lh.HCP-MMP1.annot")
    rh_hcpannot = os.path.join(atlas_dir, "rh.HCP-MMP1.annot")
    rh_hcpannot_trg = os.path.join(freesurfer_dir,SUB,"label","rh.HCP-MMP1.annot")

    command = f"{command_base} ln"\
        "  -s" \
        f" {os.path.join(freesurfer_home,'subjects','fsaverage')}" \
        f" {os.path.join(freesurfer_dir,'fsaverage')}" 
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    command = f"{command_base} ln"\
        "  -s" \
        f" {os.path.join(freesurfer_home,'subjects','lh.EC_average')}" \
        f" {os.path.join(freesurfer_dir,'lh.EC_average')}" 
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    command = f"{command_base} ln"\
        "  -s" \
        f" {os.path.join(freesurfer_home,'subjects','rh.EC_average')}" \
        f" {os.path.join(freesurfer_dir,'rh.EC_average')}" 
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    os.environ["SINGULARITYENV_SUBJECTS_DIR"]=freesurfer_dir

    command = f"{command_base} mri_surf2surf"\
        " --srcsubject fsaverage" \
        f" --trgsubject {SUB}" \
        " --hemi lh" \
        f" --sval-annot {lh_hcpannot}" \
        f" --tval {lh_hcpannot_trg}"
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    command = f"{command_base}  mri_surf2surf"\
        " --srcsubject fsaverage" \
        f" --trgsubject {SUB}" \
        " --hemi rh" \
        f" --sval-annot {rh_hcpannot}" \
        f" --tval {rh_hcpannot_trg}"
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    atlas_space_fs = newfile(workdir, atlas_file, suffix="desc-hcpmmp1_space-fs")
    command = f"{command_base} mri_aparc2aseg"\
        f"  --s {SUB}" \
        "  --old-ribbon" \
        " --annot HCP-MMP1" \
        f" --o {atlas_space_fs}" 
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    atlas_space_T1w = newfile(workdir, atlas_file, suffix="desc-hcpmmp1_space-T1w",extension=".mgz")
    rawavg=os.path.join(freesurfer_dir,SUB,"mri","rawavg.mgz")
    command = f"{command_base} mri_label2vol"\
        f"  --seg {atlas_space_fs}" \
        f"  --temp {rawavg}" \
        f"  --o {atlas_space_T1w}" \
        f"  --regheader {atlas_space_fs}" 
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    atlas_space_T1w_nii = newfile(workdir, atlas_space_T1w,suffix="desc-unordered",extension=".nii.gz")
    fs_command_base, fscontainer = getContainer(panpipe_labels,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER")
    convMGZ2NII(atlas_space_T1w,atlas_space_T1w_nii, fs_command_base)


    from panpipelines.nodes.antstransform import antstransform_proc

    panpipe_labels= updateParams(panpipe_labels,"COST_FUNCTION","NearestNeighbor")

    atlas_transform_mat = getParams(panpipe_labels,"NEWATLAS_TRANSFORM_MAT")
    
    if not atlas_transform_mat:
        atlas_transform_mat = getParams(panpipe_labels,"ATLAS_TRANSFORM_MAT")

    atlas_transform_ref = getParams(panpipe_labels,"NEWATLAS_TRANSFORM_REF")
    if not atlas_transform_ref:
        atlas_transform_ref = getParams(panpipe_labels,"ATLAS_TRANSFORM_REF")

    if atlas_transform_mat:
        CURRDIR=os.getcwd()
        os.chdir(workdir)
        results = antstransform_proc(panpipe_labels, atlas_space_T1w_nii,atlas_transform_mat, atlas_transform_ref)
        os.chdir(CURRDIR)
        atlas_space_transform = results['out_file']
    else:
        atlas_space_transform=atlas_space_T1w_nii

    hcpmmp_original = os.path.join(atlas_dir, "hcpmmp1_original.txt")
    hcpmmp_ordered = os.path.join(atlas_dir, "hcpmmp1_ordered.txt")

    # enforce int data type at this point
    command = f"{command_base} fslmaths"\
            f"  {atlas_space_transform}"\
            f" {atlas_space_transform}" \
            " -odt int"
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)


    command = f"{command_base} labelconvert"\
        f"  {atlas_space_transform}" \
        f"  {hcpmmp_original}" \
        f"  {hcpmmp_ordered}" \
        f"  {atlas_file}" 
    evaluated_command=substitute_labels(command,panpipe_labels)
    results = runCommand(evaluated_command)

    return [f"get_freesurfer_atlas_index:{hcpmmp_ordered}"]


def getAge(birthdate,refdate=None):
    from datetime import date
    if refdate is None:
        today = date.today()
    else:
        today=refdate
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age

def initTemplateFlow(TEMPLATEFLOW_HOME):
    ref1=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=2,suffix="T1w",extension=[".nii.gz"])
    ref2=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",resolution=2,suffix="T1w",extension=[".nii.gz"])
    transform1 = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",suffix="xfm",extension=[".h5"])
    transform2 = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",suffix="xfm",extension=[".h5"])
    return [[ref1,transform1],[ref2,transform2]]

def getSharedProjects(connection, subjectLabel,origProjectID,sharedProjectIDs):
    sharedProjects=[]
    REVERSE=False

    try:
        apistring = f"/data/projects/{origProjectID}/subjects/{subjectLabel}/projects"
        response = connection.get(apistring,query={"format":"json"})
        responseJson = response.json()
        if responseJson:
            results = responseJson["ResultSet"]["Result"]
            for result in results:
                if "ID" in result.keys():
                    for sharedProjectID in sharedProjectIDs:
                        if result["ID"] == sharedProjectID:
                            sharedProjects.append(sharedProjectID)

    except Exception as e:
        REVERSE=True

    if REVERSE:
            for sharedProjectID in sharedProjectIDs:
                apistring = f"/data/projects/{sharedProjectID}/subjects/{subjectLabel}/projects"
                try:
                    response = connection.get(apistring,query={"format":"json"})
                    responseJson = response.json()
                    if responseJson:
                        results = responseJson["ResultSet"]["Result"]
                        for result in results:
                            if "ID" in result.keys():
                                    if result["ID"] == origProjectID:
                                        sharedProjects.append(sharedProjectID)
                except Exception as e:
                    pass

    sharedProjectString = ",".join(sharedProjects)
    return sharedProjectString


def getBidsTSV(host,user,password,projects,targetfolder,outputdir,demographics=True,shared_project_list=["001_HML","002_HML","003_HML","004_HML"]):
    import xnat
    from pydicom import dcmread
    import fnmatch

    if not os.path.isdir(outputdir):
        os.mkdir(outputdir)

    participantsTSV=os.path.join(outputdir,'participants.tsv')
    sessionsTSV=os.path.join(outputdir,'sessions.tsv')

    participant_columns=['xnat_subject_id','xnat_subject_label','bids_participant_id','project','shared_projects','gender', 'age','scan_date','comments']
    participant_data=[]

    session_columns=['xnat_session_id','xnat_session_label','xnat_subject_id','xnat_subject_label','bids_participant_id','bids_session_id', 'project', 'shared_projects','gender', 'age','scan_date','comments']
    session_data=[]

    scantest = os.path.join(outputdir,'scantest.dcm')

    with xnat.connect(server=host,user=user, password=password) as connection:

        if projects is None:
            projects = connection.projects

        for PROJ in projects:
            try: 
                project = connection.projects[PROJ]
                UTLOGGER.info(f"Getting participant information for Project {project.id}.\n")
                # rigmarole here as iteration acting weirdly with experiments
                experiments = project.experiments
                numexps =  len(experiments)
                for expid in range(numexps):

                    print_progress(expid + 1, numexps, prefix='Progress', suffix='Complete')
                    experiment=experiments[expid]
                    xnat_session_id =""
                    xnat_session_label = ""
                    xnat_subject_id = ""
                    xnat_subject_label = ""
                    bids_participant_id = ""
                    bids_session_id = ""
                    gender = ""
                    age = ""
                    comments=""
                    scan_date=""
                    shared_projects=""


                    # _MR_ hack - some reason 003_HML MR session not storing modality 
                    if experiment.modality == 'MR' or "_MR_" in experiment.label:
                        xnat_session_id = experiment.id
                        xnat_session_label = experiment.label
                        xnat_subject_id = experiment.subject.id
                        xnat_subject_label = experiment.subject.label
                        try:
                            if (experiment.resources[targetfolder]):
                                files = experiment.resources[targetfolder].files
                                numfiles = len(files)
                                for fileid in range(numfiles):
                                    file=files[fileid]
                                    if fnmatch.fnmatch(file.path,'sub-*/ses-*/*'):
                                        bids_participant_id = file.path.split('/')[0]
                                        bids_session_id = file.path.split('/')[1]
                                        break

                                if not bids_participant_id:
                                    for fileid in range(numfiles):
                                        file=files[fileid]
                                        if fnmatch.fnmatch(file.path,'sub-*/*'):
                                            bids_participant_id = file.path.split('/')[0]
                                            bids_session_id = ''
                                            break

                            if demographics:
                                scans = experiment.scans
                                for scan_index in range(len(scans)):
                                    if "DICOM" in experiment.scans[scan_index].resources.keys():
                                        experiment.scans[scan_index].resources['DICOM'].files[0].download(scantest)
                                        ds = dcmread(scantest)
                                        gender = ds.PatientSex
                                        if ds.PatientBirthDate:
                                            agedate=datetime.datetime.strptime(ds.PatientBirthDate,"%Y%m%d")
                                        else:
                                            agedate=experiment.subject.demographics.dob 
                                        scan_date = ds.StudyDate   
                                        scandate = datetime.datetime.strptime(scan_date,"%Y%m%d")
                                        if agedate is None or agedate == '':
                                            comments = "subject age missing; " + comments
                                        else:
                                            age=getAge(agedate,scandate)
                                        break

                            shared_projects = getSharedProjects(connection, xnat_subject_label,project.id,shared_project_list)

                        except Exception as e:
                            message = 'problem parsing resource : %s.' % targetfolder
                            comments="missing bids files; " + comments
                            print(message)
                            print(str(e))

                        session_data.append([xnat_session_id,xnat_session_label,xnat_subject_id,xnat_subject_label,bids_participant_id,bids_session_id, project.id, shared_projects,gender, age,scan_date,comments])

            except Exception as e:
                message = 'problem parsing project :  %s.' % PROJ
                print (message)
                print(str(e))

        df = pd.DataFrame(session_data, columns=session_columns)
        df.to_csv(sessionsTSV,sep="\t", index=False)

        first=df.groupby('xnat_subject_id').first()
        subs_list=df['xnat_subject_id'].to_list()
        subs_set=set(subs_list)
        first['xnat_subject_id'] = sorted(subs_set)
        cols=list(first.columns.values)
        cols.pop(cols.index('xnat_subject_id'))
        cols.pop(cols.index('xnat_session_id'))
        cols.pop(cols.index('xnat_session_label'))
        cols.pop(cols.index('bids_session_id'))
        newdf=first[['xnat_subject_id'] + cols]
        newdf.to_csv(participantsTSV,sep="\t", index=False)

        if os.path.exists(scantest):
            os.remove(scantest)

# Print iterations progress
def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=50):
    """
    Call in a loop to create terminal progress bar
    https://gist.github.com/aubricus/f91fb55dc6ba5557fbab06119420dd6a
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '|' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 50, fill = '|', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    https://stackoverflow.com/questions/3173320/text-progress-bar-in-terminal-with-block-characters
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

def arrangePipelines(jsondict,pipelines=[]):
    # build up dictionary of pipelines and dependencies
    pipeline_dict={}
    drop_pipelines=[]
    for pipeline in pipelines:
        if pipeline in jsondict.keys():
            pipeline_dict[pipeline]=[]
            if "DEPENDENCY" in jsondict[pipeline]:
                dependency = jsondict[pipeline]["DEPENDENCY"]
                if not isinstance(dependency,list):
                    dependency = [dependency]
                dep_list=[]
                for dep in dependency:
                    if dep in pipelines:
                        dep_list.append(dep)

                if dep_list:
                    pipeline_dict[pipeline]=dep_list
        else:
            UTLOGGER.info(f"{pipeline} not defined in configuration file. Please check spelling. Removing from list of pipelines")
            drop_pipelines.append(pipeline)

    # Drop pipelines that are not defined
    for droppipes in drop_pipelines:
        pipelines.remove(droppipes)

    arranged_pipelines=pipelines.copy()
    # Now sort pipelines according to order of dependencies.start with first pipeline and make sure it runs after dependency.
    for pipeline in pipelines:
        arranged_pipelines = shufflePipelines(pipeline_dict, pipeline, arranged_pipelines)

    return arranged_pipelines

def shufflePipelines(pipeline_dict,pipeline,pipelines):

    pipeindex = pipelines.index(pipeline)

    newpipeindex = pipeindex
    for pipe in pipelines:
        if pipe != pipeline:
            if pipe in pipeline_dict[pipeline]:
                newpipeindex=recursePipe([newpipeindex],pipe,pipelines,pipeline_dict)

    if newpipeindex != pipeindex:
        if newpipeindex > pipeindex:
            pipelines.insert(newpipeindex+1,pipeline)
            pipelines.pop(pipeindex)


    return pipelines

def recursePipe(recurselist,pipe,pipelines,pipeline_dict):
    recurselist.append(pipelines.index(pipe))
    for dep in pipeline_dict[pipe]:
        recursePipe(recurselist,dep,pipelines,pipeline_dict)
    return max(recurselist)


def getContainer(labels_dict,nodename="",SPECIFIC=None,CONTAINERALT="PAN_CONTAINER", LOGGER=UTLOGGER):
    if SPECIFIC:
        container_run_options = getParams(labels_dict,f"{SPECIFIC}_RUN_OPTIONS")
        container_prerun = getParams(labels_dict,f"{SPECIFIC}_PRERUN")
        container = getParams(labels_dict,f"{SPECIFIC}")
        if SPECIFIC == "DUMMY_CONTAINER":
            return "",""
    else:
        container_run_options = None
        container_prerun = None
        container = None

    if container and not container_run_options:
        container_run_options = getParams(labels_dict,'CONTAINER_RUN_OPTIONS')
        if not container_run_options:
            container_run_options = ""

    if container and not container_prerun:
        container_prerun = getParams(labels_dict,'CONTAINER_PRERUN')
        if not container_prerun:
            container_prerun = ""

    if not container:
        container = getParams(labels_dict,'CONTAINER')
        if not container:
            container = getParams(labels_dict,f'{CONTAINERALT}')
            if not container:
                container = getParams(labels_dict,'NEURO_CONTAINER')
                if not container:
                    container=""

                    LOGGER.info(f"Container not defined for {nodename} node. Required commands should be accessible on local path for pipeline to succeed")
                    if container_run_options:
                        LOGGER.info(f"Note that '{container_run_options}' set as run options for non-existing container. This may cause the pipeline to fail.")
                    
                    if container_prerun:
                        LOGGER.info(f"Note that '{container_prerun}' set as pre-run options for non-existing container. This may cause the pipeline to fail.")


    # replace None by empty string
    if container is None:
        container=""
    
    if container_run_options is None:
        container_run_options=""

    if container_prerun is None:
        container_prerun=""

    command_base = f"{container_run_options} {container} {container_prerun} "
    command_base = command_base.lstrip()
    LOGGER.info("Container base run command is:")
    LOGGER.info(f"{command_base}")

    return command_base, container

def runCommand(command,LOGGER=UTLOGGER,suppress="",interactive=False):
    if suppress:
        LOGGER.info(suppress)
    else:
        LOGGER.info(command)
    evaluated_command_args = shlex.split(command)
    if suppress:
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        return "<Suppressed>"
    else:
        if not interactive:
            results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
            LOGGER.info(results.stdout)
            return results.stdout
        else:
            results = subprocess.run(evaluated_command_args)

# this is a specific function here for sdcflows fieldmaps - should move and make more general
def getAcquisition(bids_dir,participant_label,participant_session=None,suffix="asl",extension="nii.gz"):
    acq=""    
    layout = BIDSLayout(bids_dir)
    bidslist=layout.get(subject=participant_label,session=participant_session,suffix=suffix, extension=extension)
    if len(bidslist) > 0:
        bidsfile =bidslist[0]
        entities = bidsfile.get_entities()
        if "acquisition" in entities.keys():
            acq = "acq-" + entities["acquisition"]
        else:
            acq = get_bidstag("acq",bidsfile.filename)

    return acq

def getPhaseDiffSources(bids_dir,participant_label,participant_session=None,acquisition=None,datatype="fmap",suffix=['phase1','phase2','magnitude1','magnitude2','phasediff','magnitude'],extension="nii.gz"):   
    layout = BIDSLayout(bids_dir)
    bidslist = layout.get(return_type='file',subject=participant_label,session=participant_session,acquisition=acquisition,datatype=datatype,suffix=suffix,extension=extension)

    return bidslist


def getPepolarSources(bids_dir,participant_label,participant_session=None,acquisition="fmri",datatype="fmap",suffix=['epi'],extension="nii.gz"):   
    layout = BIDSLayout(bids_dir)
    bidslist = layout.get(return_type='file',subject=participant_label,session=participant_session,acquisition=acquisition,datatype=datatype,suffix=suffix,extension=extension)

    return bidslist


def get_fslparams(fsl_dict):
    params = ""
    for fsl_tag, fsl_value in fsl_dict.items():
        if "--" in fsl_tag and "---" not in fsl_tag:
            if fsl_value == "^^^":
                    params=params + " " + fsl_tag
            elif fsl_value == "###":
                UTLOGGER.info(f"Parameter {fsl_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                if fsl_value:
                    params = params + " " + fsl_tag+"=" + str(fsl_value)

        elif str(fsl_tag).upper().startswith("DUMMYKEY") and fsl_value:
                params=params + " " + fsl_value
        elif "-" in fsl_tag and "--" not in fsl_tag:
            if fsl_value == "^^^":
                    params=params + " " + fsl_tag
            elif fsl_value == "###":
                UTLOGGER.info(f"Parameter {fsl_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                if fsl_value:
                    params = params + " " + fsl_tag +" " + str(fsl_value)

        else:
            print(f"fsl tag {fsl_tag} not valid.")
    return params

def N4BiasFieldCorrection(panpipe_labels,inputfile,biascorr_output,biascorr_field=None,mask=None,dims=3,spline_spacing="[ 180 ]",convergence="[ 50x50x50x50, 0.0]",shrink_factor="1"):
    command_base, container = getContainer(panpipe_labels,nodename="N4BiasFieldCorrection",SPECIFIC="ANTS_CONTAINER",LOGGER=UTLOGGER)

    if not biascorr_field:
        biascorr_field = newfile(assocfile=biascorr_output,suffix="biascorr-field")

    ants_dict=OrderedDict()
    ants_dict = updateParams(ants_dict,"-d",str(dims))
    ants_dict = updateParams(ants_dict,"-v","1")
    ants_dict = updateParams(ants_dict,"-s",str(shrink_factor))
    ants_dict = updateParams(ants_dict,"-b",str(spline_spacing))
    ants_dict = updateParams(ants_dict,"-c",str(convergence))
    ants_dict = updateParams(ants_dict,"-i",str(inputfile))
    ants_dict = updateParams(ants_dict,"-o",f"[ {str(biascorr_output)},{biascorr_field} ]")
    ants_dict = updateParams(ants_dict,"-m",mask)

    params = get_fslparams(ants_dict)
    command=f"{command_base} N4BiasFieldCorrection"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)


def clean_up_edge(panpipe_labels, outfile, maskim, tmpnm, despike_thresh=2.1,edge_thresh=0.5):
    command_base, container = getContainer(panpipe_labels,nodename="clean_up_edge",SPECIFIC="FSL_CONTAINER",LOGGER=UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"--loadfmap",f"{str(outfile)}")
    fsl_dict = updateParams(fsl_dict,"--savefmap",f"{str(tmpnm)}_tmp_fmapfilt")
    fsl_dict = updateParams(fsl_dict,"--mask",f"{str(maskim)}")
    fsl_dict = updateParams(fsl_dict,"--despike","^^^")
    fsl_dict = updateParams(fsl_dict,"--despikethreshold",f"{str(despike_thresh)}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fugue"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(maskim)}")
    fsl_dict = updateParams(fsl_dict,"-kernel","2D")
    fsl_dict = updateParams(fsl_dict,"-ero",f"{str(tmpnm)}_tmp_eromask")

    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(maskim)}")
    fsl_dict = updateParams(fsl_dict,"-sub",f"{str(tmpnm)}_tmp_eromask")
    fsl_dict = updateParams(fsl_dict,"-thr",f"{str(edge_thresh)}")
    fsl_dict = updateParams(fsl_dict,"-bin",f"{str(tmpnm)}_tmp_edgemask")

    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(tmpnm)}_tmp_fmapfilt")
    fsl_dict = updateParams(fsl_dict,"-mas",f"{str(tmpnm)}_tmp_edgemask")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{str(tmpnm)}_tmp_fmapfiltedge")

    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(outfile)}")
    fsl_dict = updateParams(fsl_dict,"-mas",f"{str(tmpnm)}_tmp_eromask")
    fsl_dict = updateParams(fsl_dict,"-add",f"{str(tmpnm)}_tmp_fmapfiltedge")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{str(outfile)}")

    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)


def demean_image(panpipe_labels, outim, maskim, tmpnm, percentile=50):
    command_base, container = getContainer(panpipe_labels,nodename="demean_image",SPECIFIC="FSL_CONTAINER",LOGGER=UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(outim)}")
    fsl_dict = updateParams(fsl_dict,"-mas",f"{maskim}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{str(tmpnm)}_tmp_fmapmasked")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(tmpnm)}_tmp_fmapmasked")
    fsl_dict = updateParams(fsl_dict,"-k",f"{maskim}")
    fsl_dict = updateParams(fsl_dict,"-P",f"{str(percentile)}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslstats"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    subfactor = runCommand(evaluated_command,UTLOGGER).strip()

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(outim)}")
    fsl_dict = updateParams(fsl_dict,"-sub",f"{subfactor}")
    fsl_dict = updateParams(fsl_dict,"-mas",f"{maskim}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{str(outim)}")
    fsl_dict = updateParams(fsl_dict,"-odt","float")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, panpipe_labels)
    results = runCommand(evaluated_command,UTLOGGER)
