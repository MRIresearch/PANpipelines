import pandas as pd
import numpy as np
import json
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from functools import partial
import getpass
import xnat
from pydicom import dcmread
from  pydicom.multival import MultiValue as MultiValue
import datetime
import os
from collections import OrderedDict
import fnmatch
from panpipelines.utils.util_functions import *

INCLUDE_QC=False

PAN_SCANTYPES = {
    "DWI":["DTI_MB_3SHELL_mono_TE91_ORIG","DTI_MB_3SHELL 0 1000 2000 mono te 91_ORIG","DTI_MB_3SHELL_0_1K_2K"],
    "DWI_RPE" : ["DTI_MB_3SHELL RPE_ORIG","DTI_MB_3SHELL_RPE"],
    "MPRAGE" : ["Accelerated Sagittal MPRAGE","Sagittal 3D Accelerated MPRAGE","Accelerated Sagittal MPRAGE (MSV21)"],
    "RSFMRI" : ["RS-FMRI-MB-high_resolution","Axial fcMRI _EYES OPEN","Axial fcMRI _EYES_Open_plus"],
    "FLAIR" : ["Sagittal 3D FLAIR","Sagittal 3D FLAIR","Sagittal 3D FLAIR (MSV21)"] ,
    "PCASL" : ["WIP SOURCE - Axial 3D PCASL"],
    "PCASL_M0" : ["Axial 3D M0"],
    "PASL" : ["PASL_PRODUCT_PLD-2750"],
    "PASL_M0" : ["PASL_PRODUCT_PLD-2750 MO"],
    "PASL_LEGACY": ["AXIAL 3D PASL plus M0","Axial 3D PASL plus M0"],
    "MEGRE" : ["Axial 3D ME T2 GRE","Axial 3D ME T2 GRE_noT2*"],
    "T2HIPPO" : ["HighResHippocampus","HighResHippoObliqueperpenHIPPO"],
    "T2SPACE" : ["Sagittal 3D T2 SPACE","3D_Brain_VIEW_T2"]
}

PAN_OPTIONAL = ["T2HIPPO"]
PAN_LEGACY = ["T2SPACE","PASL_LEGACY"]
PASL_OPTIONAL = ["PCASL","PCASL_M0"]
PCASL_OPTIONAL = ["PASL","PASL_M0"]

CANDO_STRUCT_REQS = ["MPRAGE"]

CANDO_PASL_REQS = ["PASL","PASL_M0","MPRAGE"]
CANDO_PASLSDC_REQS = ["PASL","PASL_M0","MPRAGE","MEGRE"]
CANDO_PASLSDC_FMRI_REQS = ["PASL","PASL_M0","MPRAGE","MEGRE","RSFMRI"]
CANDO_PASLSDC_DWI_REQS = ["PASL","PASL_M0","MPRAGE","DWI","DWI_RPE"]

CANDO_PASLLEGACY_REQS = ["PASL_LEGACY","MPRAGE"]
CANDO_PASLLEGACYSDC_REQS = ["PASL_LEGACY","MPRAGE","MEGRE"]
CANDO_PASLLEGACYSDC_FMRI_REQS = ["PASL_LEGACY","MPRAGE","MEGRE","RSFMRI"]
CANDO_PASLLEGACYSDC_DWI_REQS = ["PASL_LEGACY","MPRAGE","DWI","DWI_RPE"]

CANDO_PCASL_REQS = ["PCASL","PCASL_M0","MPRAGE"]
CANDO_PCASLSDC_REQS = ["PCASL","PCASL_M0","MPRAGE","MEGRE"]
CANDO_PCASLSDC_FMRI_REQS = ["PCASL","PCASL_M0","MPRAGE","MEGRE","RSFMRI"]
CANDO_PCASLSDC_DWI_REQS = ["PCASL","PCASL_M0","MPRAGE","DWI","DWI_RPE"]

CANDO_DWI_REQS = ["DWI","MPRAGE"]
CANDO_DWISDC_REQS = ["DWI","DWI_RPE","MPRAGE"]

CANDO_RSFMRI_REQS = ["RSFMRI","MPRAGE"]
CANDO_RSFMRISDC_REQS = ["RSFMRI","MPRAGE","MEGRE"]
CANDO_RSFMRISDC_DWI_REQS = ["RSFMRI","MPRAGE","DWI","DWI_RPE"]

TARGET_PROJECT="PAN_250_1"

###########################################################



PAN_RELEASE="pan_release"
PAN_SITE="pan_site"
SUBJECT_LABEL="xnat_subject_label"
HMLID="hml_id"
XNATID_ORIG="orig_xnat_subject_label"
MCID="participant_id_parent"
P2ID = "p2_id"

ORIG_PROJECT="orig_pan_site"
GENDER = "gender"
YOB = "yob"
SESSION_LABEL = "session_label"
SESSION_MODALITY = "session_modality"
SESSION_SCANDATE="session_scandate"
SESSION_NOTES="session_notes"
BIDS_SUBJECT="subject_id"
BIDS_SESSION="session_id"
CANDO_STRUCT = "cando_struct"
CANDO_DWI = "cando_dwi"
CANDO_DWI_SDC = "cando_dwi_sdc"
CANDO_PASL = "cando_pasl"
CANDO_PASL_SDC = "cando_pasl_sdc"
CANDO_PASL_SDC_FMRI= "cando_pasl_sdc_fmri"
CANDO_PASL_SDC_DWI= "cando_pasl_sdc_dwi"
CANDO_PASLLEGACY = "cando_pasllegacy"
CANDO_PASLLEGACY_SDC = "cando_pasllegacy_sdc"
CANDO_PASLLEGACY_SDC_FMRI= "cando_pasllegacy_sdc_fmri"
CANDO_PASLLEGACY_SDC_DWI= "cando_pasllegacy_sdc_dwi"
CANDO_PCASL = "cando_pcasl"
CANDO_PCASL_SDC = "cando_pcasl_sdc"
CANDO_PCASL_SDC_FMRI = "cando_pcasl_sdc_fmri"
CANDO_PCASL_SDC_DWI = "cando_pcasl_sdc_dwi"
CANDO_RSFMRI = "cando_rsfmri"
CANDO_RSFMRI_SDC = "cando_rsfmri_sdc"
CANDO_RSFMRI_SDC_DWI = "cando_rsfmri_sdc_dwi"
MRI_SCAN_ORDER = "mri_scan_order"
MRI_MISSING_SCANS = "mri_missing_scans"
MRI_MISSING_OPTIONAL_SCANS = "mri_missing_optional_scans"
MRI_PROBLEM_SCANS = "mri_problem_scans"
BIDS_AVAIL = "bids_avail"
BIDSQC_STATUS = "bidsqc_status"
BIDSQC_FAIL = "bidsqc_fail"
MRIQC_AVAIL = "mriqc_avail"
QSIPREP_AVAIL = "qsiprep_avail"
EDDYQC_AVAIL = "eddyqc_avail"
ASLPREP_AVAIL = "aslprep_avail"
FMRIPREP_AVAIL = "fmriprep_avail"
RADNORMAL = "radnormal"

CANDO_ASL = "cando_asl"
CANDO_ASL_SDC = "cando_asl_sdc"
CANDO_ASL_SDC_FMRI= "cando_asl_sdc_fmri"
CANDO_ASL_SDC_DWI= "cando_asl_sdc_dwi"

MANUFACTURER = "manufacturer"
STATION_NAME="station_name"
DEVICE_SERIAL_NUMBER="device_serial_number"
SOFTWARE_VERSION="software_versions"
MANUFACTURER_MODEL_NAME="manufacturer_model_name"
IMPLEMENTATION_VERSION_NAME="implementation_version_name"

CREATION_DATE="row_creation_datetime"


table_header = []
#table_header.append(PAN_RELEASE)
table_header.append(PAN_SITE)
table_header.append(SUBJECT_LABEL)
table_header.append(HMLID)
#table_header.append(XNATID_ORIG)
#table_header.append(MCID)
#table_header.append(P2ID)
#table_header.append(ORIG_PROJECT)
#table_header.append(GENDER)
#table_header.append(YOB)
table_header.append(SESSION_LABEL)
table_header.append(SESSION_MODALITY)
table_header.append(SESSION_SCANDATE)
table_header.append(SESSION_NOTES)
table_header.append(BIDS_SUBJECT)
table_header.append(BIDS_SESSION)
table_header.append(CANDO_STRUCT)
table_header.append(CANDO_DWI)
table_header.append(CANDO_DWI_SDC)
table_header.append(CANDO_PASL)
table_header.append(CANDO_PASL_SDC)
table_header.append(CANDO_PASL_SDC_FMRI)
table_header.append(CANDO_PASL_SDC_DWI)
table_header.append(CANDO_PASLLEGACY)
table_header.append(CANDO_PASLLEGACY_SDC)
table_header.append(CANDO_PASLLEGACY_SDC_FMRI)
table_header.append(CANDO_PASLLEGACY_SDC_DWI)
table_header.append(CANDO_PCASL)
table_header.append(CANDO_PCASL_SDC)
table_header.append(CANDO_PCASL_SDC_FMRI)
table_header.append(CANDO_PCASL_SDC_DWI)
table_header.append(CANDO_RSFMRI)
table_header.append(CANDO_RSFMRI_SDC)
table_header.append(CANDO_RSFMRI_SDC_DWI)
table_header.append(MRI_SCAN_ORDER)
table_header.append(MRI_MISSING_SCANS)
table_header.append(MRI_MISSING_OPTIONAL_SCANS)
table_header.append(MRI_PROBLEM_SCANS)
table_header.append(BIDSQC_STATUS)
table_header.append(BIDSQC_FAIL)
table_header.append(BIDS_AVAIL)
table_header.append(MRIQC_AVAIL)
table_header.append(QSIPREP_AVAIL)
table_header.append(EDDYQC_AVAIL)
table_header.append(ASLPREP_AVAIL)
table_header.append(FMRIPREP_AVAIL)
table_header.append(MANUFACTURER)
table_header.append(STATION_NAME)
table_header.append(DEVICE_SERIAL_NUMBER)
table_header.append(SOFTWARE_VERSION)
table_header.append(MANUFACTURER_MODEL_NAME)
table_header.append(IMPLEMENTATION_VERSION_NAME)
table_header.append(CREATION_DATE)

if INCLUDE_QC:
    mriqc_headers=[]
    mriqc_headers_t1w=["cjv","cnr","efc","fber","fwhm_avg","qi_1","qi_2","snr_total"]
    mriqc_t1w_label = "rec-defaced_T1w"
    mriqc_headers_t2w=["cjv","cnr","efc","fber","fwhm_avg","qi_1","qi_2","snr_total"]
    mriqc_t2w_label = "acq-hippo_T2w"
    mriqc_headers_bold=["efc","fber","fd_mean","gcor","gsr_x","gsr_y","snr","tsnr"]
    mriqc_bold_label = "task-rest_bold"            
    mriqc_headers.extend([f"MRIQC.{mriqc_t1w_label}.{x}" for x in mriqc_headers_t1w])
    mriqc_headers.extend([f"MRIQC.{mriqc_t2w_label}.{x}" for x in mriqc_headers_t2w])
    mriqc_headers.extend([f"MRIQC.{mriqc_bold_label}.{x}" for x in mriqc_headers_bold])
    table_header.extend(mriqc_headers)

    qsiprepqc_headers=[]
    qsiprepqc_headers_imageQC=["mean_fd","max_fd","max_rotation","max_translation","raw_num_bad_slices","t1_num_bad_slices"]
    qsiprepqc_imageQC_label="desc-ImageQC_dwi"
    qsiprepqc_headers.extend([f"QSIPREPQC.{qsiprepqc_imageQC_label}.{x}" for x in qsiprepqc_headers_imageQC])
    table_header.extend(qsiprepqc_headers)

    eddyqc_headers=[]
    eddyqc_headers_qc=["qc_mot_abs","qc_mot_rel","qc_outliers_tot","qc_cnr_avg"]
    eddyqc_qc_label="qc"            
    eddyqc_headers.extend([f"EDDYQC.{eddyqc_qc_label}.{x}" for x in eddyqc_headers_qc])
    table_header.extend(eddyqc_headers)

    aslprepqc_headers=[]
    aslprepqc_headers_cbf=["FD", "cbfQEI","GMmeanCBF","WMmeanCBF","Gm_Wm_CBF_ratio","NEG_CBF_PERC"]
    aslprepqc_cbf_label="desc-qualitycontrol_cbf"           
    aslprepqc_headers.extend([f"ASLPREPQC.{aslprepqc_cbf_label}.{x}" for x in aslprepqc_headers_cbf])
    table_header.extend(aslprepqc_headers)

table_header.append(RADNORMAL)


##################################################################

def getProject(p2site):
    if p2site:
        if p2site == "UA":
            return "001_HML"
        elif p2site == "UM":
            return "002_HML"
        elif p2site == "EU":
            return "003_HML"
        elif p2site == "JH":
            return "004_HML"
        elif p2site == "PAN250":
            return "PAN_250_1"
        else:
            print(f"P2site {p2site} not recognized")
            return ''
    else:
        print("P2site not defined.")
        return ''

def getSite(project):
    if project:
        if project == "001_HML":
            return "UA"
        elif project == "002_HML":
            return "UM"
        elif project == "003_HML":
            return "EU"
        elif project == "004_HML":
            return "JH"
        elif project == "PAN_250_1":
            return "PAN250"
        else:
            print(f"Project {project} not recognized")
            return ''
    else:
        print("P2site not defined.")
        return ''


def getParams(pardict, key, default=None):
    if key is not None and pardict is not None:
        if key in pardict:
            if not pardict[key] and default:
                return default
            else:
                return pardict[key]
    return default

def loadParams(pardict, key, value, update=True):
    if key and value:
        if key in pardict:
            if not pardict[key] or update:
                pardict[key]=value
    #    else:
    #        pardict[key]=value
    return pardict

def cleanServer(server):
    server.strip()
    if server[-1] == '/':
        server = server[:-1]
    if server.find('http') == -1:
        server = 'https://' + server
    return server

def _path_exists(path, parser):
    """Ensure a given path exists."""
    if path is None or not Path(path).exists():
        raise parser.error(f"Path does not exist: <{path}>.")
    return Path(path).expanduser().absolute()

def parse_params():
    parser = ArgumentParser(description="BIDSQC")
    PathExists = partial(_path_exists, parser=parser)
    parser.add_argument("csvout", type=Path, help="The directory where output files are stored")
    parser.add_argument("--projects", help="Projects", required=False, nargs='*')
    parser.add_argument("--excluded_participants", help="Participants to exclude", required=False, nargs='*')
    parser.add_argument("--host", help="XNAT host", required=True)
    parser.add_argument("--credentials", type=PathExists, help="credential file")
    parser.add_argument("--pipeline_config_file", type=Path, help="Pipeline Config File")
    return parser


def getMissingScans(sequence,project=None):
    if project:
        if project == "004_HML":
            return list(set(list(PAN_SCANTYPES.keys())).difference(sequence).difference(PAN_OPTIONAL).difference(PCASL_OPTIONAL).difference(PAN_LEGACY))
        else:
            return list(set(list(PAN_SCANTYPES.keys())).difference(sequence).difference(PAN_OPTIONAL).difference(PASL_OPTIONAL).difference(PAN_LEGACY))
    else: 
        return list(set(list(PAN_SCANTYPES.keys())).difference(sequence).difference(PAN_OPTIONAL).difference(PAN_LEGACY))

def getMissingOptionalScans(sequence,project=None):
    if project:
        if project == "004_HML":
            return list(set(list(PAN_SCANTYPES.keys())).difference(sequence).difference(PCASL_OPTIONAL).difference(PAN_LEGACY).intersection(PAN_OPTIONAL))
        else:
            return list(set(list(PAN_SCANTYPES.keys())).difference(sequence).difference(PASL_OPTIONAL).difference(PAN_LEGACY).intersection(PAN_OPTIONAL))
    else: 
        return list(set(list(PAN_SCANTYPES.keys())).difference(sequence).difference(PAN_LEGACY).intersection(PAN_OPTIONAL))

def findPANScanType(scantype):
    for pan_type, pan_val in PAN_SCANTYPES.items():
        if scantype in pan_val:
            return pan_type
    return None

def getSequence(experiment):

    # roundabout way to do this as iterator on scans in xnatpy is a little wonky
    scans = experiment.scans
    sequence=[]
    for scan_index in range(len(scans)):
        scan = experiment.scans[scan_index]
        scan_id = scan.id
        scan_type = scan.type
        pan_type = findPANScanType(scan_type)
        if pan_type:
            sequence.append(pan_type)

    # hack for interoperability scans
    if len(sequence) > 50:
        sequence = list(set(sequence))

    return sequence


def cando_proc(REQS,sequence,missingscans, problemscans=[],struct_sessions={}):
    validscans = list(set(sequence).difference(missingscans).difference(problemscans))
    missing = list(set(REQS).difference(validscans))
    if not missing:
        return "Y"
    elif len(missing) == 1 and missing[0] == "MPRAGE" and struct_sessions and structsAvailable(struct_sessions):
        return "S"
    else:
        return "N"

def structsAvailable(struct_sessions):
    structAvail=False
    for itemkey, itemvalue in struct_sessions.items():
        if itemvalue == "Y":
            structAvail = True
    return structAvail


def structsOverSessions(experiments,orig_project):
    struct_sessions={}

    for exp_index in range(len(experiments)):
        experiment = experiments[exp_index]
        exp_label = experiment.label
        if experiment.modality == 'MR' or '_MR_' in experiment.label:
            sequence = getSequence(experiment)
            missing_scans = getMissingScans(sequence,orig_project)
            struct_sessions[exp_label] = cando_proc(CANDO_STRUCT_REQS,sequence,missing_scans)

    return struct_sessions


def getQCMeasures(files, headers, table_row):

    json_dict = {}
    for header in headers:
        sourcename = header.split(".")[1]
        if sourcename not in json_dict.keys():
            json_dict[sourcename] = None
            for file_index in range(len(files)):
                file = files[file_index]
                if f"{sourcename}.json" in file.name:
                    file_name=os.path.join("/tmp",os.path.basename(file.name))
                    file.download(file_name)
                    with open(file_name,'r') as in_file:
                        file_json = json.load(in_file)
                    if file_json:
                        json_dict[sourcename] = file_json
                    else:
                        json_dict[sourcename] = None
                    break


    for header in headers:
        prefix = header.split(".")[0]
        sourcename = header.split(".")[1]
        field = header.split(".")[2]
        file_json = json_dict[sourcename]
        if file_json is not None:
            if field in file_json.keys():
                loadParams(table_row,header,str(file_json[field]))
            else:
                loadParams(table_row,header,"")
        else:
            loadParams(table_row,header,"")

    return table_row


def getQCMeasuresCSV(files, headers, table_row):


    json_dict = {}
    for header in headers:
        sourcename = header.split(".")[1]
        if sourcename not in json_dict.keys():
            json_dict[sourcename] = None
            for file_index in range(len(files)):
                file = files[file_index]
                if f"{sourcename}.csv" in file.name:
                    file_name=os.path.join("/tmp",os.path.basename(file.name))
                    file.download(file_name)
                    if os.path.exists(file_name):
                        df = pd.read_table(file_name,sep=",")
                        json_dict[sourcename] = df
                    break


    for header in headers:
        prefix = header.split(".")[0]
        sourcename = header.split(".")[1]
        field = header.split(".")[2]
        data_f = json_dict[sourcename]
        if data_f is not None:
            if field in data_f.columns.tolist():
                measure_f = df[field].iloc[0]
                loadParams(table_row,header,str(measure_f))
            else:
                loadParams(table_row,header,"")
        else:
            loadParams(table_row,header,"")

    return table_row


def appendText(comments,message,seperator=","):
    if comments:
        comments = comments + ": " + message
    else:
        comments = message
    return comments

def loadText(comments,message,replace = True):
    if not comments:
        comments=message
    elif replace:
        comments=message
    return comments

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

def getSubjectRows(xnatid, connection, table_header,project=None, table_row={},all_dups=[], hmlid="",do_share=False):
    table_rows = []
    return table_rows

def iterateSessions(connection,xnatid,table_row={},all_dups=[],hmlid="",do_share=True):
    table_rows = []
    return table_rows


def getSubjectCustomField(connection, subject, field):
    try:
        return  subject.fields[field]
    except:
        print(f"problem obtaining subject custom field : {field}")
        if field == "hmlid":
            return subject.label
        else:
            return ""

def canProc(df):
    dfy = df == "Y"
    dfs = df == "S"
    if pd.DataFrame.any(dfy):
        return "Y"
    elif pd.DataFrame.any(dfs):
        return "S"
    else:
        return "N"


def canProcList(dflist):
    df = pd.concat(dflist,axis=1)
    dfy = df == "Y"
    dfs = df == "S"
    if pd.DataFrame.any(pd.DataFrame.any(dfy)):
        return "Y"
    elif pd.DataFrame.any(pd.DataFrame.any(dfs)):
        return "S"
    else:
        return "N"


def getBidsQC(host,user,password,projects,csvout,excluded_participants=[],LOGFILE=None,pipeline_config_file=None):
  
    labels_dict={}
    if pipeline_config_file:
        panpipeconfig_file=str(pipeline_config_file)
        if os.path.exists(pipeline_config_file):
           print(f"{pipeline_config_file} exists.")
           with open(pipeline_config_file,'r') as infile:
               labels_dict = json.load(infile)


    bidsqcOutdir=os.path.abspath(os.path.dirname(csvout))

    if not os.path.isdir(bidsqcOutdir):
        os.makedirs(bidsqcOutdir,exist_ok=True)

    try:
        table_data = []

        scantest = os.path.join("/tmp",'scantest.dcm')

        with xnat.connect(server=host,user=user,password=password) as connection:

            if not projects:
                projects = connection.projects
            
            if len(projects) == 1:
                pan_release_t = projects[0]
            else:
                pan_release_t = "Latest"

            for PROJ in list(set(projects)):
                project = connection.projects[PROJ]

                project_t = project.id

                bidsqcOutProjdir=os.path.join(bidsqcOutdir,project.id)
                if not os.path.isdir(bidsqcOutProjdir):
                    os.mkdir(bidsqcOutProjdir)

                bidsqcDetailsOutdir=os.path.join(bidsqcOutProjdir,'Details')
                if not os.path.isdir(bidsqcDetailsOutdir):
                    os.mkdir(bidsqcDetailsOutdir)

                subjects = project.subjects
                for sub_index in range(len(subjects)):

                    subject_row = []

                    table_row = initializeRow()
                    loadParams(table_row,PAN_RELEASE,pan_release_t)
                    loadParams(table_row,PAN_SITE,project_t)

                    subject = subjects[sub_index]

                    subject_t = subject.label
                    loadParams(table_row,SUBJECT_LABEL,subject_t)

                    gender_t = subject.demographics.gender
                    loadParams(table_row,GENDER,gender_t)

                    loadParams(table_row,HMLID,getSubjectCustomField(connection,subject,"hmlid"))
                    loadParams(table_row,XNATID_ORIG,getSubjectCustomField(connection,subject,"xnatorigid"))
                    loadParams(table_row,MCID,getSubjectCustomField(connection,subject,"mcid"))
                    loadParams(table_row,P2ID,getSubjectCustomField(connection,subject,"p2id"))
                    orig_project = getSubjectCustomField(connection,subject,"site")
                    loadParams(table_row,ORIG_PROJECT,orig_project)

                    yob_t = ""
                    dob = subject.demographics.dob
                    if dob:
                        yob_t = datetime.datetime.strftime(dob,"%Y")
                    loadParams(table_row,YOB,yob_t)

                    experiment_t = 'None'
                    loadParams(table_row,SESSION_LABEL,experiment_t)

                    Manufacturer_t=""
                    StationName_t = ""
                    DeviceSerialNumber_t = ""
                    SoftwareVersions_t=""
                    ManufacturerModelName_t=""
                    ImplementationversionName_t=""

                    experiments = subject.experiments

                    if len(experiments) < 1:
                        subject_row.append(table_row)
                      
                    struct_sessions=structsOverSessions(experiments,orig_project)

                    for exp_index in range(len(experiments)):

                        session_table_row = table_row.copy()

                        experiment = experiments[exp_index]
                        experiment_t = experiment.label
                        loadParams(session_table_row,SESSION_LABEL,experiment_t)

                        
                        if experiment.modality == 'MR' or '_MR_' in experiment.label:

                            loadParams(session_table_row,SESSION_MODALITY,"MR")

                            scandate_t = datetime.datetime.strftime(experiment.date,"%Y%m%d")
                            loadParams(session_table_row,SESSION_SCANDATE,scandate_t)
                         
                            scans = experiment.scans

                            scan_sequence = getSequence(experiment)
                            loadParams(session_table_row,MRI_SCAN_ORDER,"|".join(scan_sequence))

                            missing_scans = getMissingScans(scan_sequence,orig_project)
                            loadParams(session_table_row,MRI_MISSING_SCANS,"|".join(missing_scans))

                            missing_optional_scans = getMissingOptionalScans(scan_sequence,orig_project)
                            loadParams(session_table_row,MRI_MISSING_OPTIONAL_SCANS,"|".join(missing_optional_scans))


                            for scan_index in range(len(scans)):
                                if "DICOM" in experiment.scans[scan_index].resources.keys():
                                    try:
                                        experiment.scans[scan_index].resources['DICOM'].files[0].download(scantest)
                                        ds = dcmread(scantest)
                                        if not gender_t:
                                            gender_t = ds.PatientSex
                                            loadParams(session_table_row,GENDER,gender_t)

                                        if not yob_t:
                                            if ds.PatientBirthDate:
                                                agedate=datetime.datetime.strptime(ds.PatientBirthDate,"%Y%m%d")
                                                yob_t = datetime.datetime.strftime(agedate,"%Y")
                                                loadParams(session_table_row,YOB,yob_t)

                                        if not scandate_t:
                                            dcm_scandate = ds.StudyDate
                                            scandate = datetime.datetime.strptime(dcm_scandate,"%Y%m%d")
                                            scandate_t = datetime.datetime.strftime(scandate,"%Y%m%d")
                                            loadParams(session_table_row,SESSION_SCANDATE,scandate_t)

                                        if not Manufacturer_t:
                                            Manufacturer_t=ds.Manufacturer
                                            loadParams(session_table_row,MANUFACTURER,Manufacturer_t) 
                                        if not StationName_t:
                                            StationName_t = ds.StationName
                                            loadParams(session_table_row,STATION_NAME,StationName_t) 
                                        if not DeviceSerialNumber_t:
                                            DeviceSerialNumber_t = ds.DeviceSerialNumber
                                            loadParams(session_table_row,DEVICE_SERIAL_NUMBER,DeviceSerialNumber_t) 
                                        if not SoftwareVersions_t:
                                            SoftwareVersions_t = ds.SoftwareVersions 
                                            if isinstance(SoftwareVersions_t,MultiValue):
                                                SoftwareVersions_t = list(SoftwareVersions_t)[0]
                                            loadParams(session_table_row,SOFTWARE_VERSION,SoftwareVersions_t) 
                                        if not ManufacturerModelName_t:
                                            ManufacturerModelName_t = ds.ManufacturerModelName
                                            loadParams(session_table_row,MANUFACTURER_MODEL_NAME,ManufacturerModelName_t) 
                                        if not ImplementationversionName_t:
                                            ImplementationversionName_t = ds.file_meta.ImplementationVersionName
                                            loadParams(session_table_row,IMPLEMENTATION_VERSION_NAME,ImplementationversionName_t) 
                                        break

                                    except Exception as e:
                                        pass


                            notes_t = experiment.note
                            loadParams(session_table_row,SESSION_NOTES,notes_t)


                            # get blank mriqc measures for situations where MRIQC resource doesn't exist
                            if INCLUDE_QC:
                                session_table_row = getQCMeasures([],mriqc_headers,session_table_row)
                                session_table_row = getQCMeasuresCSV([],qsiprepqc_headers,session_table_row)
                                session_table_row = getQCMeasures([],eddyqc_headers,session_table_row)
                                session_table_row = getQCMeasuresCSV([],aslprepqc_headers,session_table_row)

                            radread_t=""
                            assessors = experiment.assessors
                            for assessor_index in range(len(assessors)):
                                assessor = assessors[assessor_index]
                                if assessor.__xsi_type__ == "rad:radiologyReadData":
                                    finding = assessor.get("finding/normal_status")
                                    if not radread_t:
                                        radread_t = str(finding)
                                        loadParams(session_table_row,RADNORMAL,radread_t)
                                    else:
                                        radread_t = radread_t + " : " + str(finding)
                                        loadParams(session_table_row,RADNORMAL,radread_t)

                            resources = experiment.resources
                            problemscans=[]
                            for res_index in range(len(resources)):
                                resource = resources[res_index]

                                if resource.label == 'BIDS-AACAZ':
                                    bids_participant_id=""
                                    bids_session_id = ""
                                    files = resource.files
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

                                    loadParams(session_table_row,BIDS_SUBJECT,bids_participant_id)
                                    loadParams(session_table_row,BIDS_SESSION,bids_session_id)


                                if resource.label == 'BIDSQC-AACAZ':
                                    fail_t = [x for x in resource.files if 'FAIL.txt' in x]
                                    if len(fail_t) > 0:
                                        bidsqc_t = 'FAIL'
                                        loadParams(session_table_row,BIDSQC_STATUS,bidsqc_t)
                                        files = resource.files
                                        for file_index in range(len(files)):
                                            file = files[file_index]
                                            if file.name == 'FAIL.txt':
                                                fail_file = os.path.join(bidsqcDetailsOutdir,'{}_{}_FAIL.txt'.format(subject_t,experiment_t))
                                                file.download(fail_file)
                                                with open(fail_file,'r') as in_file:
                                                    fail_text_lines = in_file.readlines()
                                                details_t = ''.join(fail_text_lines).replace('\n\n',' | ').replace('\n','')
                                                loadParams(session_table_row,BIDSQC_FAIL,details_t)

                                    pass_t = [x for x in resource.files if 'PASS.txt' in x]
                                    if len(pass_t) > 0:
                                        bidsqc_t = 'PASS'
                                        loadParams(session_table_row,BIDSQC_STATUS,bidsqc_t)
                                      
                                    # attempt heuristic here
                                    if bidsqc_t == "FAIL":
                                        details_parts = details_t.split("|")
                                        hippo_missing = [x for x in details_parts if "acq-hippo_T2w.json json file not found" in x]
                                        pasl_pe = [x for x in details_parts if "acq-prod_asl.json::PhaseEncodingDirection is *DIFFERENT*" in x]
                                        dwirpe_pe = [x for x in details_parts if "dir-AP_epi.json::PhaseEncodingDirection is *DIFFERENT*" in x]
                                        rsfmri_pe = [x for x in details_parts if "task-rest_bold.json::PhaseEncodingDirection is *DIFFERENT*" in x]

                                        if (len(details_parts) == 1 and hippo_missing) or (len(details_parts) == 2 and hippo_missing and not details_parts[1].strip()):
                                            bidsqc_t = 'PASS'
                                            loadParams(session_table_row,BIDSQC_STATUS,bidsqc_t)

                                        if pasl_pe:
                                            problemscans.append("PASL")

                                        if dwirpe_pe:
                                            problemscans.append("DWI_RPE")

                                        elif rsfmri_pe:
                                            problemscans.append("RSFMRI")


                                bids_t = "N"
                                if resource.label == 'BIDS-AACAZ' and resource.files is not None and len(resource.files) > 0:
                                    bids_t = "Y"
                                    loadParams(session_table_row,BIDS_AVAIL,bids_t)

                                mriqc_t = "N"
                                if resource.label == 'MRIQC-AACAZ' and resource.files is not None and len(resource.files) > 0:
                                    mriqc_t = "Y"
                                    loadParams(session_table_row,MRIQC_AVAIL,mriqc_t)
                                    if INCLUDE_QC:
                                        session_table_row = getQCMeasures(resource.files,mriqc_headers,session_table_row)

                                fmriprep_t = "N"
                                if resource.label == 'FMRIPREP-AACAZ' and resource.files is not None and len(resource.files) > 0:
                                    fmriprep_t = "Y"
                                    loadParams(session_table_row,FMRIPREP_AVAIL,fmriprep_t)

                                qsiprep_t = "N"
                                if resource.label == 'QSIPREP-AACAZ' and resource.files is not None and len(resource.files) > 0:
                                    qsiprep_t = "Y"
                                    loadParams(session_table_row,QSIPREP_AVAIL,qsiprep_t)
                                    if INCLUDE_QC:
                                        session_table_row = getQCMeasuresCSV(resource.files,qsiprepqc_headers,session_table_row)

                                eddyqc_t = "N"
                                if resource.label == 'EDDYQC-AACAZ' and resource.files is not None and len(resource.files) > 0:
                                    eddyqc_t = "Y"
                                    loadParams(session_table_row,EDDYQC_AVAIL,eddyqc_t)
                                    if INCLUDE_QC:
                                        session_table_row = getQCMeasures(resource.files,eddyqc_headers,session_table_row)

                                aslprep_t = "N"
                                if resource.label == 'ASLPREP-AACAZ' and resource.files is not None and len(resource.files) > 0:
                                    aslprep_t = "Y"
                                    loadParams(session_table_row,ASLPREP_AVAIL,aslprep_t)
                                    if INCLUDE_QC:
                                        session_table_row= getQCMeasuresCSV(resource.files,aslprepqc_headers,session_table_row)

                            # address problem scans and analysis possibility
                            loadParams(session_table_row,MRI_PROBLEM_SCANS,"|".join(problemscans))


                        elif experiment.modality == 'US' or '_US_' in experiment.label:
                            loadParams(session_table_row,SESSION_MODALITY,"US")

                            scandate_t = datetime.datetime.strftime(experiment.date,"%Y%m%d")
                            loadParams(session_table_row,SESSION_SCANDATE,scandate_t)
                        else:
                            loadParams(session_table_row,SESSION_MODALITY,"UNKNOWN")

                            scandate_t = datetime.datetime.strftime(experiment.date,"%Y%m%d")
                            loadParams(session_table_row,SESSION_SCANDATE,scandate_t)


                        if getParams(session_table_row,SESSION_MODALITY) == "MR":
                            struct_sessions[experiment_t] = cando_proc(CANDO_STRUCT_REQS,scan_sequence,missing_scans,problemscans=problemscans,struct_sessions=struct_sessions)

                        
                        subject_row.append(session_table_row)

                    for session_row in subject_row:
                        if getParams(session_row,SESSION_MODALITY) == "MR":
                            session_sequence = getParams(session_row,MRI_SCAN_ORDER).split("|")
                            session_missing = getParams(session_row,MRI_MISSING_SCANS).split("|")
                            session_problem = getParams(session_row,MRI_PROBLEM_SCANS).split("|")

                            struct_poss  = cando_proc(CANDO_STRUCT_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_STRUCT,struct_poss)

                            dwi_poss = cando_proc(CANDO_DWI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_DWI,dwi_poss)

                            dwi_sdc_poss = cando_proc(CANDO_DWISDC_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_DWI_SDC,dwi_sdc_poss)

                            rsfmri_poss = cando_proc(CANDO_RSFMRI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_RSFMRI,rsfmri_poss)

                            rsfmri_sdc_poss = cando_proc(CANDO_RSFMRISDC_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_RSFMRI_SDC,rsfmri_sdc_poss)

                            rsfmri_dwi_sdc_poss = cando_proc(CANDO_RSFMRISDC_DWI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_RSFMRI_SDC_DWI,rsfmri_dwi_sdc_poss)

                            pasl_poss = cando_proc(CANDO_PASL_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASL,pasl_poss)

                            pasllegacy_poss = cando_proc(CANDO_PASLLEGACY_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASLLEGACY,pasllegacy_poss)

                            pcasl_poss = cando_proc(CANDO_PCASL_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PCASL,pcasl_poss)

                            pasl_sdc_poss = cando_proc(CANDO_PASLSDC_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASL_SDC,pasl_sdc_poss)

                            pasllegacy_sdc_poss = cando_proc(CANDO_PASLLEGACYSDC_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASLLEGACY_SDC,pasllegacy_sdc_poss)

                            pcasl_sdc_poss = cando_proc(CANDO_PCASLSDC_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PCASL_SDC,pcasl_sdc_poss)

                            pasl_fmri_sdc_poss = cando_proc(CANDO_PASLSDC_FMRI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASL_SDC_FMRI,pasl_fmri_sdc_poss)

                            pasllegacy_fmri_sdc_poss = cando_proc(CANDO_PASLLEGACYSDC_FMRI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASLLEGACY_SDC_FMRI,pasllegacy_fmri_sdc_poss)

                            pcasl_fmri_sdc_poss = cando_proc(CANDO_PCASLSDC_FMRI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PCASL_SDC_FMRI,pcasl_fmri_sdc_poss)

                            pasl_dwi_sdc_poss = cando_proc(CANDO_PASLSDC_DWI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASL_SDC_DWI,pasl_dwi_sdc_poss)

                            pasllegacy_dwi_sdc_poss = cando_proc(CANDO_PASLLEGACYSDC_DWI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PASLLEGACY_SDC_DWI,pasllegacy_dwi_sdc_poss)

                            pcasl_dwi_sdc_poss = cando_proc(CANDO_PCASLSDC_DWI_REQS,session_sequence,session_missing,problemscans=session_problem,struct_sessions=struct_sessions)
                            loadParams(session_row,CANDO_PCASL_SDC_DWI,pcasl_dwi_sdc_poss)

                        loadParams(session_row,CREATION_DATE,get_datetimestring_utc())

                    if not subject_t in excluded_participants:
                        table_data = appendTableRows(subject_row, table_data)


            bidsqc_df = pd.DataFrame(table_data, columns=table_header)
            bidsqc_df = bidsqc_df.sort_values(by=[HMLID])
            bidsqc_df.reset_index(drop=True, inplace=True)
            bidsqc_df.to_csv(csvout,index=False) 

            #bidsqc_mr_df = bidsqc_df[bidsqc_df["SESSION_MODALITY"] == "MR"]
            #bidsqc_mr_df.reset_index(drop=True, inplace=True)
            #bidsqc_mr_df.to_csv("./bidsqc/paninfo_release_250_bidsqc_mr",index=False) 

            # csv = "/xdisk/ryant/chidiugonna/Development/repos/PAN_Release_250/scripts/bidsqc/paninfo_release_250_bidsqc.csv"
            # bidsqc_df = df = pd.read_table(csv,sep=",")
            #subject_core_df = bidsqc_df[[PAN_RELEASE,HMLID, HMLID_REC, XNATID_ORIG,MCID,P2ID,P2SITE_ORIG,ORIG_PROJECT,GENDER,YOB]]
            #subject_cando_df = bidsqc_mr_df[[HMLID,CANDO_STRUCT,CANDO_DWI,CANDO_DWI_SDC,CANDO_PASL,CANDO_PASL_SDC,CANDO_PASL_SDC_FMRI,CANDO_PCASL,CANDO_PCASL_SDC,CANDO_PCASL_SDC_FMRI,CANDO_RSFMRI,CANDO_RSFMRI_SDC]]

            #subject_core_df = subject_core_df.drop_duplicates()

            subject_proc_df = bidsqc_df.groupby([HMLID]).apply(lambda s: pd.Series( { 
                "SUBJECT_" + CANDO_STRUCT : canProc(s[CANDO_STRUCT]),
                "SUBJECT_" +CANDO_DWI : canProc(s[CANDO_DWI]),
                "SUBJECT_" +CANDO_DWI_SDC : canProc(s[CANDO_DWI_SDC]),
                "SUBJECT_" +CANDO_PASL : canProc(s[CANDO_PASL]),
                "SUBJECT_" +CANDO_PASL_SDC : canProc(s[CANDO_PASL_SDC]),
                "SUBJECT_" +CANDO_PASL_SDC_FMRI : canProc(s[CANDO_PASL_SDC_FMRI]),
                "SUBJECT_" +CANDO_PASL_SDC_DWI : canProc(s[CANDO_PASL_SDC_DWI]),
                "SUBJECT_" +CANDO_PASLLEGACY : canProc(s[CANDO_PASLLEGACY]),
                "SUBJECT_" +CANDO_PASLLEGACY_SDC : canProc(s[CANDO_PASLLEGACY_SDC]),
                "SUBJECT_" +CANDO_PASLLEGACY_SDC_FMRI : canProc(s[CANDO_PASLLEGACY_SDC_FMRI]),
                "SUBJECT_" +CANDO_PASLLEGACY_SDC_DWI : canProc(s[CANDO_PASLLEGACY_SDC_DWI]),
                "SUBJECT_" +CANDO_PCASL : canProc(s[CANDO_PCASL]),
                "SUBJECT_" +CANDO_PCASL_SDC : canProc(s[CANDO_PCASL_SDC]),
                "SUBJECT_" +CANDO_PCASL_SDC_FMRI : canProc(s[CANDO_PCASL_SDC_FMRI]),
                "SUBJECT_" +CANDO_PCASL_SDC_DWI : canProc(s[CANDO_PCASL_SDC_DWI]),
                "SUBJECT_" +CANDO_RSFMRI : canProc(s[CANDO_RSFMRI]),
                "SUBJECT_" +CANDO_RSFMRI_SDC : canProc(s[CANDO_RSFMRI_SDC]),
                "SUBJECT_" +CANDO_RSFMRI_SDC_DWI : canProc(s[CANDO_RSFMRI_SDC_DWI]),
                "SUBJECT_" +CANDO_ASL : canProcList([s[CANDO_PASL],s[CANDO_PCASL],s[CANDO_PASLLEGACY]]),
                "SUBJECT_" +CANDO_ASL_SDC : canProcList([s[CANDO_PASL_SDC],s[CANDO_PCASL_SDC],s[CANDO_PASLLEGACY_SDC]]),
                "SUBJECT_" +CANDO_ASL_SDC_FMRI : canProcList([s[CANDO_PASL_SDC_FMRI],s[CANDO_PCASL_SDC_FMRI],s[CANDO_PASLLEGACY_SDC_FMRI]]),
                "SUBJECT_" +CANDO_ASL_SDC_DWI : canProcList([s[CANDO_PASL_SDC_DWI],s[CANDO_PCASL_SDC_DWI],s[CANDO_PASLLEGACY_SDC_DWI]])
            }))


            consolidated_df = pd.merge(bidsqc_df, subject_proc_df,  how='left', left_on=[HMLID], right_on = [HMLID])

            subject_csvout = os.path.splitext(csvout)[0] + "_subjectproc.csv"
            consolidated_df.to_csv(subject_csvout,index=False) 

            for header in consolidated_df.columns:
                if header.upper().startswith("MRIQC.") or header.upper().startswith("EDDYQC.") or header.upper().startswith("ASLPREPQC.") or header.upper().startswith("QSIPREPQC.") or '_AVAIL' in header.upper():
                    consolidated_df.pop(header) 

            subject_reduced_csvout = os.path.splitext(csvout)[0] + "_reduced_subjectproc.csv"
            consolidated_df.to_csv(subject_reduced_csvout,index=False)

            bidsqc_table_name = "xnat_mri_sessions.csv"
            if labels_dict and "BIDSQC_TABLENAME" in labels_dict.keys():
                bidsqc_table_name = getParams(labels_dict,"BIDSQC_TABLENAME")


            pan_mri_info_csvout = os.path.join(os.path.dirname(csvout),bidsqc_table_name)
            search_df = consolidated_df[(consolidated_df[SESSION_MODALITY]=="MR")]

            for header in search_df.columns:
                if 'CANDO' in header.upper() or 'RADNORMAL' in header.upper() or "MODALITY" in header.upper():
                    search_df.pop(header) 

            cols=list(search_df.columns.values)
            cols.pop(cols.index(HMLID))
            cols.pop(cols.index(BIDS_SUBJECT))
            cols.pop(cols.index(BIDS_SESSION))
            newdf=search_df[[HMLID] + [BIDS_SUBJECT] + [BIDS_SESSION] + cols]
            sorted_df = newdf.sort_values(by = [HMLID], ascending = [True])
            sorted_df.reset_index(drop=True,inplace=True)
            sorted_df.to_csv(pan_mri_info_csvout,sep=",", index=False)
            pan_mri_info_csvout_metadata = create_metadata(pan_mri_info_csvout,None, metadata = {"Script":"paninfo_bidsqc.py","Description":"Information about missing scans and scan issues"})

            if labels_dict:
                labels_dict["METADATA_FILE"]=pan_mri_info_csvout_metadata 
                labels_dict["OUTPUT_FILE"]=pan_mri_info_csvout
                export_labels(labels_dict,pipeline_config_file)


    except Exception as e:
        message = f"problem identifying BIDSQC files in {project.id} :  %s.\n{e}" 
        print (message)
        ACTION_OK=False

def main():
    parser=parse_params()
    args, unknown_args = parser.parse_known_args()
    csvout = str(args.csvout)

    host = cleanServer(args.host)

    if args.projects:
        projects = args.projects
    else:
        projects = []

    if args.excluded_participants:
        excluded_participants = args.excluded_participants
    else:
        excluded_participants = []

    pipeline_config_file = None
    if args.pipeline_config_file:
        if Path(args.pipeline_config_file).exists():
            pipeline_config_file = str(args.pipeline_config_file)


    credentials = args.credentials
    user=None
    password=None
    if credentials:
        with open(credentials, 'r') as infile:
            cred_dict = json.load(infile)
            user = getParams(cred_dict,"user")
            password = getParams(cred_dict,"password")

    if user and password:
        print(f"user defined as {user} in credentials file {credentials}. Password also provided in same file.")
    elif user and not password:
        print(f"user defined as {user} in credentials file {credentials}. Password not provided in file. please enter password to match user.")
        password = getpass.getpass()
    elif not user and password:
        print(f"user not defined ain credentials file {credentials}. However a password was supplied. Please provide user that matches password.")
        user = input("User: ")
    elif not user and not password:
        print(f"Please provide user and password credentials.")
        user = input("User: ")
        password = getpass.getpass()

    getBidsQC(host,user,password,projects,csvout,excluded_participants=excluded_participants,pipeline_config_file=pipeline_config_file)


# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
