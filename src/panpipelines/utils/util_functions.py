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
    return arg is not None and (arg == 'Y' or arg == '1' or arg == 'True' or arg == 'true')

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


def substitute_labels(expression,panpipe_labels):
    if isinstance(expression,str):
        braced_vars = re.findall(r'\<.*?\>',expression)
        for braced_var in braced_vars:
            if braced_var == '<CWD>':
                expression = expression.replace(braced_var,str(os.getcwd()))
            else:
                unbraced_var = braced_var.replace('<','').replace('>','')
                lookup_var = getParams(panpipe_labels,unbraced_var)
                if isinstance(lookup_var,str) and lookup_var is not None:
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

def add_labels(config_dict,labels_dict):  
    # Process Labels
    for itemkey,itemvalue in config_dict.items():
            updateParams(labels_dict,itemkey,itemvalue)

    return labels_dict

def process_labels(config_json,config_file,labels_dict,pipeline=None,uselabel=True):  
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
            updateParams(labels_dict,itemkey,itemvalue)

    return labels_dict


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

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER>"\
            " Text2Vest " + newfsldesign_text + " " + newfsldesign
        evaluated_command=substitute_labels(command, panpipe_labels)
        os.system(evaluated_command)
        panpipe_labels = updateParams(panpipe_labels,"FSL_DESIGN",newfsldesign)


        if fslcontrast_text is not None and os.path.exists(fslcontrast_text):
            newfslcontrast=os.path.join(outputdir,os.path.basename(fslcontrast_text).split(".")[0] + '.con')
            command="singularity run --cleanenv --no-home <NEURO_CONTAINER>"\
            " Text2Vest " + fslcontrast_text + " " + newfslcontrast
            evaluated_command=substitute_labels(command, panpipe_labels)
            os.system(evaluated_command)
            panpipe_labels = updateParams(panpipe_labels,"FSL_CONTRAST",newfslcontrast)
        else:
            print("TEXT_FSL_CONTRAST Contrast not defined or doed not exist")


        if fslftest_text is not None and os.path.exists(fslftest_text):
            newfslftest=os.path.join(outputdir,os.path.basename(fslftest_text).split(".")[0] + '.fts')
            command="singularity run --cleanenv --no-home <NEURO_CONTAINER>"\
            " Text2Vest " + fslftest_text + " " + newfslftest
            evaluated_command=substitute_labels(command, panpipe_labels)
            os.system(evaluated_command)
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


def getSubjectBids(labels_dict,bids_dir,participant_label,xnat_project,user,password):

    if not os.path.isdir(os.path.join(bids_dir,"sub-"+participant_label)):
        print("BIDS folder for {} not present. Downloading started from XNAT.".format(participant_label))
        command="singularity run --cleanenv --no-home <XNATDOWNLOAD_CONTAINER> python /src/xnatDownload.py downloadSubjectSessions"\
                " BIDS-AACAZ "+bids_dir+\
                " --host <XNAT_HOST>"\
                " --subject "+participant_label+\
                " --project "+xnat_project+\
                " --user " + user + \
                " --password " + password

        evaluated_command=substitute_labels(command, labels_dict)
        os.system(evaluated_command)
    else:
        print("BIDS folder for {} already present. No need to download".format(participant_label))


def get_freesurfer_hippostats(stats_file, prefix="",participant_label=""):
    if not prefix is None and not prefix =="":
        prefix=prefix+"."
    else:
        prefix =""

    with open(stats_file,"r") as in_file:
        lines = in_file.readlines()

    table_columns = [x.split(" ")[-1] for x in lines]
    table_columns = [x.replace('\n','') for x in table_columns]
    table_columns = table_columns[1:]
    table_columns =[ prefix + x  + ".Volume" for x in table_columns]
    table_values = [x.split()[-2] for x in lines]
    table_values = table_values[1:]

    if len(table_columns) > 0 and len(table_values) > 0 and len(table_columns) == len(table_values):
        cum_df = pd.DataFrame([table_values])
        cum_df.columns = table_columns
        if participant_label is not None and not participant_label == "":
            cum_df.insert(0,"subject_id",["sub-"+participant_label])
        return cum_df
    else:
        return None



def get_freesurfer_genstats(stats_file,columns, prefix="",participant_label=""):

    if not prefix is None and not prefix =="":
        prefix=prefix+"."
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
                    header_list.append(prefix + header + ".{}".format(itemkey))
                    value=line.split()[itemvalue]
                    value_list.append(value)
    
    if len(header_list) > 0 and len(value_list) > 0 and len(header_list) == len(value_list):
        cum_df = pd.DataFrame([value_list])
        cum_df.columns = header_list
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

def create_array(participants, participants_file):
    df = pd.read_table(participants_file)
    if participants is not None and len(participants) > 0:
        array=[]
        for participant in participants:
            array.append(str(df[df["xnat_subject_label"]==participant].index.values[0] + 1))

        array.sort()
        return  ",".join(array)
    else:
        return "1:" + str(len(df))

def get_projectmap(participants, participants_file):
    df = pd.read_table(participants_file)

    if participants is not None and len(participants) > 0:
        project_list=[]
        for participant in participants:
            project_list.append(str(df[df["xnat_subject_label"]==participant].project.values[0]))
        return  [ participants, project_list ]
    else:
        participant_list = df["xnat_subject_label"].tolist()
        project_list = df["project"].tolist()
        return  [ participant_list, project_list ]


def create_script(header,template,panpipe_labels, script_file):
    with open(header,"r") as infile:
        headerlines=infile.readlines()

    with open(template,"r") as infile:
        templatelines = infile.readlines()

    newscript=[]
    header = "".join(headerlines)
    newscript.append(header)

    for templateline in templatelines:
        newscript.append(substitute_labels(templateline, panpipe_labels))

    with open(script_file,"w") as outfile:
        outfile.writelines(newscript)


def getDependencies(job_ids,panpipe_labels,logging=None):
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
                dependency_string = f"--dependency=afterany{job_ids_string}"               


        else:
            if pipeline_dependency in job_ids.keys():
                job_id = job_ids[pipeline_dependency]
                if job_id is not None:
                    dependency_string = f"--dependency=afterany:{job_id}"

    return dependency_string



def submit_script(participants, participants_file, pipeline, panpipe_labels,job_ids, analysis_level, logging=None, script_dir=None):
    headerfile=getParams(panpipe_labels,"SLURM_HEADER")
    templatefile=getParams(panpipe_labels,"SLURM_TEMPLATE")
    datelabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") 

    script_base=pipeline + "_" + datelabel
   
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
    
    outlog =f"log-%A_%a_{pipeline}_{datelabel}.panout"
    jobname = f"{pipeline}_pan"

    array = create_array(participants, participants_file)

    command = "sbatch"\
        " --job-name " + jobname +\
        " --output " + outlog + \
        " --array=" + array + \
        " " + dependencies + \
        " " + script_file 
    
    evaluated_command = substitute_labels(command,panpipe_labels)
    updateParams(panpipe_labels, "SLURM_COMMAND", evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)

    export_labels(panpipe_labels,labels_file)

    CURRDIR=os.getcwd()
    os.chdir(script_dir)

    if logging:
        logging.info(evaluated_command)

    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    if logging:
        logging.info(results.stdout)
    else:
        print(results.stdout)
 
    os.chdir(CURRDIR)

    return results.stdout.decode().split()[3]

def getGlob(globstring,default_result=""):
    glob_results = glob.glob(globstring)
    return getFirstFromList(glob_results,default_result)

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
    

    try:
        ENV_PROCS = getParams(panpipe_labels,"ENV_PROCS")
        if ENV_PROCS is not None and ENV_PROCS in os.environ.keys():
            env_count = int(os.environ[ENV_PROCS])
        procnum_list.append(env_count)
    except ValueError as ve:
        pass
    
    return int(np.min(np.array(procnum_list)))


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
    new_roi=newfile(trans_workdir, roi_in, suffix="desc-label")
    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
        f"  {roi_in}" +\
        PROBTHRESH +\
        " -bin "\
        f" -mul {roi_value}" \
        f" {new_roi}"
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

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


    if os.path.exists(atlas_file):
        command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
            f"  {new_roi_transformed}"\
            f" -add {atlas_file}" +\
            LOWTHRESH +\
            HIGHTHRESH +\
            f" {atlas_file}"
    else:
        command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
            f" {new_roi_transformed}"\
            f" {atlas_file}" 
    
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    return atlas_file


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
        add_atlas_roi(atlas_file, roi, roi_value, panpipe_labels,high_thresh=roi_value,prob_thresh=prob_thresh,roi_transform=roi_transform)

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

    if low_thresh:
        LOWTHRESH=f" -thr {low_thresh}"
    else:
        LOWTHRESH=""

    roicount=0
    numrois=len(roi_list)
    roi_files=[]
    for roi_in in roi_list:       
        # store roi in work dir\
        roicount=roicount+1
        new_roi=newfile(workdir, roi_in,suffix="desc-bin")
        command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
            f"  {roi_in}" +\
            LOWTHRESH +\
            HIGHTHRESH +\
            " -bin "\
            f" {new_roi}"
        evaluated_command = substitute_labels(command,panpipe_labels)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        roi_files.append(new_roi)

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
            roi_files_transformed.append(results['out_file'])
        else:
            new_roi_transform_file= newfile(trans_workdir, new_roi)
            shutil.move(roi_files[roi_num], new_roi_transform_file)
            roi_files_transformed.append(new_roi_transform_file)
        
    if roi_files_transformed:
        roi_string=" ".join(roi_files_transformed)
        command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmerge"\
            " -t" \
            f" {atlas_file}" +\
            " " + roi_string

        evaluated_command = substitute_labels(command,panpipe_labels)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

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
    for roi in roi_list:

        # using fsl for manipulations, so convert freesurfer files to nifti
        if Path(roi).suffix == ".mgz":

            mgzdir = os.path.join(out_dir,'roi_mgz_temp')
            if not os.path.isdir(mgzdir):
                os.makedirs(mgzdir)

            NEUROIMG=getParams(panpipe_labels,"NEURO_CONTAINER")
            roi_nii = newfile(mgzdir,roi,extension=".nii.gz")
            convMGZ2NII(roi, roi_nii, NEUROIMG)
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
                command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslroi"\
                    f"  {roi}" \
                    f" {new_roi}" \
                    f" {vol}" \
                    " 1" 
                evaluated_command = substitute_labels(command,panpipe_labels)
                evaluated_command_args = shlex.split(evaluated_command)
                results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                new_roi_list.append(new_roi)
                if roi_transform:
                    roi_transform_list.append(roi_transform)

        else:
            if explode3d:
                atlas_dict,atlas_list=get_avail_labels(roi)
                for thresh in atlas_list:
                    new_roi=newfile(workdir,roi, prefix=f"{roi_count:0>5}_{thresh:0>5}",suffix="desc-roi")
                    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
                        f" {roi}" \
                        f" -thr {thresh}" \
                        f" -uthr {thresh}" \
                        " -bin "\
                        f" {new_roi}"
                    evaluated_command = substitute_labels(command,panpipe_labels)
                    evaluated_command_args = shlex.split(evaluated_command)
                    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                    new_roi_list.append(new_roi)
                    if roi_transform:
                        roi_transform_list.append(roi_transform)
          
            else:
                new_roi=newfile(workdir,roi, prefix=f"{roi_count:0>5}",suffix="desc-roi")
                command = "cp"\
                " " + roi +\
                " " + new_roi
                evaluated_command = substitute_labels(command,panpipe_labels)
                evaluated_command_args = shlex.split(evaluated_command)
                results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
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

def get_freesurferatlas_index(atlas_file,lutfile,atlas_index,avail_only=False):
    with open(lutfile,'r') as infile:
        lutlines=infile.readlines()

    lut_dict={}
    for lut_line in lutlines:
        lut_list = lut_line.split()
        if lut_list and lut_list[0].isdigit():           
            lut_roinum = int(lut_list[0])
            lut_roiname = lut_list[1]
            lut_rgba = ",".join(lut_list[2:])
            lut_dict[lut_roinum] = {}
            lut_dict[lut_roinum]["LabelName"]=lut_roiname
            lut_dict[lut_roinum]["RGBA"]=lut_rgba

    atlas_dict={}
    atlas_img = nib.load(atlas_file)
    atlas_data = atlas_img.get_fdata()
    max_roi_num = int(np.max(atlas_data))
    for roi_num in range(1,max_roi_num+1):
        if avail_only:
            num_voxels=np.count_nonzero(atlas_data == roi_num)
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



    atlas_index_list=[]
    atlas_key_list=list(atlas_dict.keys())
    atlas_key_list.sort()
    for atlas_key in atlas_key_list:
        atlas_index_list.append(atlas_dict[atlas_key]["LabelName"])
    
    atlas_index_out = "\n".join(atlas_index_list)
    if atlas_index:
        with open(atlas_index,"w") as outfile:
            outfile.write(atlas_index_out)

    return atlas_dict,atlas_index_out

            
def create_3d_hcppmmp1_aseg(atlas_file,roi_list,panpipe_labels):
    out_dir = os.path.dirname(atlas_file)
    workdir = os.path.join(out_dir,"hcpmmp1_workdir")
    if not os.path.isdir(workdir):
        os.makedirs(workdir)

    NEUROIMG = getParams(panpipe_labels,"NEURO_CONTAINER")
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

    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> ln"\
        "  -s" \
        f" {os.path.join(freesurfer_home,'subjects','fsaverage')}" \
        f" {os.path.join(freesurfer_dir,'fsaverage')}" 
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> ln"\
        "  -s" \
        f" {os.path.join(freesurfer_home,'subjects','lh.EC_average')}" \
        f" {os.path.join(freesurfer_dir,'lh.EC_average')}" 
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> ln"\
        "  -s" \
        f" {os.path.join(freesurfer_home,'subjects','rh.EC_average')}" \
        f" {os.path.join(freesurfer_dir,'rh.EC_average')}" 
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+freesurfer_dir+" mri_surf2surf"\
        " --srcsubject fsaverage" \
        f" --trgsubject {SUB}" \
        " --hemi lh" \
        f" --sval-annot {lh_hcpannot}" \
        f" --tval {lh_hcpannot_trg}"
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+freesurfer_dir+" mri_surf2surf"\
        " --srcsubject fsaverage" \
        f" --trgsubject {SUB}" \
        " --hemi rh" \
        f" --sval-annot {rh_hcpannot}" \
        f" --tval {rh_hcpannot_trg}"
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    atlas_space_fs = newfile(workdir, atlas_file, suffix="desc-hcpmmp1_space-fs")
    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+freesurfer_dir+" mri_aparc2aseg"\
        f"  --s {SUB}" \
        "  --old-ribbon" \
        " --annot HCP-MMP1" \
        f" --o {atlas_space_fs}" 
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    atlas_space_T1w = newfile(workdir, atlas_file, suffix="desc-hcpmmp1_space-T1w",extension=".mgz")
    rawavg=os.path.join(freesurfer_dir,SUB,"mri","rawavg.mgz")
    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+freesurfer_dir+" mri_label2vol"\
        f"  --seg {atlas_space_fs}" \
        f"  --temp {rawavg}" \
        f"  --o {atlas_space_T1w}" \
        f"  --regheader {atlas_space_fs}" 
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    atlas_space_T1w_nii = newfile(workdir, atlas_space_T1w,suffix="desc-unordered",extension=".nii.gz")
    convMGZ2NII(atlas_space_T1w,atlas_space_T1w_nii,NEUROIMG)


    from panpipelines.nodes.antstransform import antstransform_proc

    panpipe_labels= updateParams(panpipe_labels,"COST_FUNCTION","NearestNeighbor")
    panppe_labels = updateParams(panpipe_labels,"OUTPUT_TYPE","int")
    atlas_transform_mat = getParams(panpipe_labels,"NEWATLAS_TRANSFORM_MAT")
    atlas_transform_ref = getParams(panpipe_labels,"NEWATLAS_TRANSFORM_REF")
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

    command = "singularity run --cleanenv --no-home <NEURO_CONTAINER> labelconvert"\
        f"  {atlas_space_transform}" \
        f"  {hcpmmp_original}" \
        f"  {hcpmmp_ordered}" \
        f"  {atlas_file}" 
    evaluated_command = substitute_labels(command,panpipe_labels)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    return [f"get_freesurfer_atlas_index:{hcpmmp_ordered}"]




