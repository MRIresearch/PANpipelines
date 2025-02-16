from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import nibabel as nb
from bids import BIDSLayout
from nipype import logging as nlogging
import json
from collections import OrderedDict
import numpy as np

IFLOGGER=nlogging.getLogger('nipype.interface')

ASL_INPUT="-i"
ASL_OUTPUT="-o"
CALIBRATION="-c"
IAF="--iaf"
IBF="--ibf"
RPTS="--rpts"
CASL="--casl"
BOLUS="--bolus"
TIS="--tis"
TR="--tr"
CMETHOD="--cmethod"
FIXBOLUS="--fixbolus"
FIXBAT="--fixbat"
MC="--mc"
PVCORR="--pvcorr"
FSLANAT="--fslanat"
DEBUG="--debug"
REGIONANALYSIS="--region-analysis"
WHITEPAPER="--wp"

FMAP="--fmap"
FMAPMAG="--fmapmag"
FMAPMAGBRAIN="--fmapmagbrain"
ECHOSPACING="--echospacing"
PEDIR="--pedir"

IS_PRESENT="^^^"
IGNORE="###"

def splitASL(asl_input,command_base,work_dir,labels_dict,m0_index="0",m0_size="1",asl_index="1",asl_size="-1"):
    new_asl_input = newfile(outputdir=work_dir, assocfile=asl_input, suffix=f"desc-asl")
    params = f"{asl_input}"\
        f" {new_asl_input}" \
        f" {asl_index}" \
        f" {asl_size}" 

    command=f"{command_base} fslroi"\
        " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    runCommand(evaluated_command,IFLOGGER)

    new_m0_input = newfile(outputdir=work_dir, assocfile=asl_input, suffix=f"desc-m0")
    params = f"{asl_input}"\
        f" {new_m0_input}" \
        f" {m0_index}" \
        f" {m0_size}" 

    command=f"{command_base} fslroi"\
        " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    runCommand(evaluated_command,IFLOGGER)

    return new_asl_input, new_m0_input


def scaleASL(asl_input, command_base, scale_factor,work_dir, basil_dict,labels_dict):

    new_asl_input = newfile(outputdir=work_dir, assocfile=asl_input, suffix=f"scale-{scale_factor}")
    params = f"{asl_input}"\
        f" -mul {scale_factor}" \
        f" {new_asl_input}" \
        " -odt float"

    command=f"{command_base} fslmaths"\
        " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    runCommand(evaluated_command,IFLOGGER)
    basil_dict = updateParams(basil_dict,ASL_INPUT,new_asl_input)
    
    return basil_dict

def getFmapSources(bids_dir,subject,session,fmap_mode="phasediff"):
    if fmap_mode == "phasediff":
        return getPhaseDiffSources(bids_dir,subject,session)
    elif fmap_mode == "pepolar":
        return getPepolarSources(bids_dir,subject,session)
    else:
        return []
    

def process_sdcflows_fieldmap(fieldmap_dir,layout, asljson , asl_acq, basil_dict, labels_dict, command_base, work_dir,bids_dir,subject,session,fmap_mode="phasediff"):
    fmapjson = getGlob(os.path.join(fieldmap_dir,"*desc-preproc_fieldmap.json"))
    if not fmapjson:
        fmapjson = os.path.join(fieldmap_dir,f"sub-{subject}_ses-{session}_desc-preproc_fieldmap.json")
        fmapdict={}
        fmapdict["RawSources"] = getFmapSources(bids_dir,subject,session,fmap_mode)
        fmapdict["Units"] = "Hz"
        export_labels(fmapdict,fmapjson)
    else:
        with open(fmapjson,"r") as infile:
            fmapdict=json.load(infile)
        if fmapdict:
            sources=[]
            Units = ""
            if "RawSources" in fmapdict.keys():
                sources = fmapdict["RawSources"]
            if not sources:
                fmapdict["RawSources"] = getFmapSources(bids_dir,subject,session,fmap_mode)
                export_labels(fmapdict,fmapjson)

            if "Units" in fmapdict.keys():
                Units = fmapdict["Units"]
            if not Units:
                fmapdict["Units"] = "Hz"
                export_labels(fmapdict,fmapjson)

    return process_fmriprep_fieldmap(fieldmap_dir,layout, asljson , asl_acq, basil_dict, labels_dict, command_base, work_dir,fmap_mode=fmap_mode)


def process_fmriprep_fieldmap(fmriprep_fieldmap_dir,layout, asljson , asl_acq, basil_dict, labels_dict, command_base, work_dir,fmap_mode="fmriprep"):
    IFLOGGER.info(f"Preparing fieldmap from {fmap_mode} for use in SDC.")
    fmap = getGlob(os.path.join(fmriprep_fieldmap_dir,"*desc-preproc_fieldmap.nii.gz"))
    fmaprads = newfile(work_dir,assocfile=fmap,intwix="desc-rads")
    fmapjson = getGlob(os.path.join(fmriprep_fieldmap_dir,"*desc-preproc_fieldmap.json"))
    xnat_project = getParams(labels_dict,"PARTICIPANT_XNAT_PROJECT")
    xnat_shared_project = getParams(labels_dict,"PARTICIPANT_XNAT_SHARED_PROJECT")

    IFLOGGER.info(f"Fieldmap located at {fmap}")
    fmapdict={}
    if fmapjson:
        with open(fmapjson,"r") as infile:
            fmapdict=json.load(infile)

    if "Units" in fmapdict.keys():
        if fmapdict["Units"] == "Hz":
            
            mult = 2 * np.pi
            IFLOGGER.info(f"Multiply {fmap} by {mult} to Convert from Hz to {fmaprads} in rad/s")

            params = f"{fmap}"\
                    f" -mul {mult}" \
                    f" {fmaprads}" \
                    " -odt float"

            command=f"{command_base} fslmaths"\
                        " "+params

            evaluated_command=substitute_labels(command, labels_dict)
            runCommand(evaluated_command,IFLOGGER)
            basil_dict = updateParams(basil_dict,FMAP,fmaprads)
            
        elif fmapdict["Units"] == "rad/s":
            IFLOGGER.info(f"{fmap} ialready in rad/s. Rename to {fmaprads}.")
            fmaprads = fmap
            basil_dict = updateParams(basil_dict,FMAP,fmaprads)
        else:
            unkunits = fmapdict["Units"]
            IFLOGGER.info(f"Units {unkunits} not recognized.")
           
    
    if os.path.exists(fmaprads): 
        fmapmag = getGlob(os.path.join(fmriprep_fieldmap_dir,"*desc-magnitude_fieldmap.nii.gz"))
        fmapmag_brain = newfile(work_dir,assocfile=fmapmag,intwix="desc-brain")
        IFLOGGER.info(f"Create brain-extracted {fmapmag_brain} from {fmapmag}.")   

        params = f"{fmapmag}"\
            f" {fmapmag_brain}" \
            " -R"

        command=f"{command_base} bet"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        runCommand(evaluated_command,IFLOGGER)

        basil_dict = updateParams(basil_dict,FMAPMAG,fmapmag)
        basil_dict = updateParams(basil_dict,FMAPMAGBRAIN,fmapmag_brain)

    echospacing = None
    if os.path.exists(fmapmag_brain):
        
        if "EffectiveEchoSpacing" in asljson.keys():
            echospacing = asljson["EffectiveEchoSpacing"]
            IFLOGGER.info(f"Echospacing {echospacing} obtained from BIDS metadata") 
        
        if not echospacing:
            IFLOGGER.info(f"Echospacing not found in BIDS metadata. Attempting to retrieve from config file.") 
            ECHOSPACING_DICT= getParams(labels_dict,"ASL_ECHOSPACING")
            if ECHOSPACING_DICT is not None and isinstance(ECHOSPACING_DICT, dict):
                if asl_acq in ECHOSPACING_DICT.keys():
                    if ECHOSPACING_DICT[asl_acq] is not None and isinstance(ECHOSPACING_DICT[asl_acq], dict):
                        if xnat_project in ECHOSPACING_DICT[asl_acq].keys():
                            echospacing = ECHOSPACING_DICT[asl_acq][xnat_project]

                        elif xnat_shared_project in ECHOSPACING_DICT[asl_acq].keys():
                            echospacing = ECHOSPACING_DICT[asl_acq][xnat_shared_project]
                        
                        elif "default" in ECHOSPACING_DICT[asl_acq].keys():
                            echospacing = ECHOSPACING_DICT[asl_acq]["default"]

                        else:
                            IFLOGGER.info(f"ASL_ECHOSPACING Dictionary keys {ECHOSPACING_DICT[asl_acq].keys()} not valid") 

                    else:
                        echospacing = ECHOSPACING_DICT[asl_acq]
     
            if echospacing:
                IFLOGGER.info(f"Echospacing {echospacing} obtained from config file.")   
            else:
                IFLOGGER.error(f"Echospacing not defined. Fieldmap correction will not work.") 
                raise ValueError("<ASL_ECHOSPACING> not defined in config file for fieldmap processing.")

        basil_dict = updateParams(basil_dict,ECHOSPACING,echospacing) 
        pedir_ijk = asljson["PhaseEncodingDirection"]
        IFLOGGER.info(f"PE Direction of ASL is {pedir_ijk}")   
        pedir_fsl = pedir_ijk.replace('j-','-y').replace('j','y').replace('i-','-x').replace('i','x').replace('k-','-z').replace('k','z')
        IFLOGGER.info(f"PE Direction of ASL converted to {pedir_fsl} for BASIL.")    
        basil_dict = updateParams(basil_dict,PEDIR,pedir_fsl)


    return basil_dict

# work in progress
def process_fsl_prepare_fieldmap(layout, asl_json,basil_dict,labels_dict, asljson, asl_acq, command_base, work_dir):

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')
    xnat_project = getParams(labels_dict,"PARTICIPANT_XNAT_PROJECT")
    xnat_shared_project = getParams(labels_dict,"PARTICIPANT_XNAT_SHARED_PROJECT")

    phase1 = layout.get(subject=participant_label,suffix='phase1', extension='nii.gz')
    echo1=None
    if phase1:
        phase1_md = phase1[0].get_metadata()
        if phase1_md:
            echo1=phase1_md["EchoTime"]
        phase1 = phase1[0].path

    phase2 = layout.get(subject=participant_label,suffix='phase2', extension='nii.gz')
    echo2=None
    if phase2:
        phase2_md = phase2[0].get_metadata()
        if phase2_md:
            echo2=phase2_md["EchoTime"]
        phase2 = phase2[0].path
    
    deltaTE=None
    deltaTEms=None
    if echo1 and echo2:
        deltaTE=(float(echo2) - float(echo1))
        deltaTEms=(1000 * deltaTE)

    mag1 = layout.get(subject=participant_label,suffix='magnitude1', extension='nii.gz')
    if mag1:
        mag1=mag1[0].path
    mag2 = layout.get(subject=participant_label,suffix='magnitude2', extension='nii.gz')
    if mag2:
        mag2=mag2[0].path

    magnitude = mag1
    magnitude_biascorr = newfile(work_dir,magnitude,suffix="biascorr")
    biascorr_biasfield = newfile(work_dir,magnitude,suffix="biascorr-biasfield")
    N4BiasFieldCorrection(labels_dict,magnitude,magnitude_biascorr,biascorr_biasfield)

    magnitude_biascorr_brain = newfile(work_dir,magnitude_biascorr,suffix="brain")
    command_base, container = getContainer(labels_dict,nodename="process_fsl_prepare_fieldmap",SPECIFIC="FSL_CONTAINER",LOGGER=IFLOGGER)
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{magnitude_biascorr}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{magnitude_biascorr_brain}")
    fsl_dict = updateParams(fsl_dict,"-R","^^^")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} bet"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{magnitude_biascorr_brain}")
    fsl_dict = updateParams(fsl_dict,"-ero",f"{magnitude_biascorr_brain}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    magnitude_biascorr_brain_mask = newfile(work_dir,magnitude_biascorr_brain,suffix="mask")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{magnitude_biascorr_brain}")
    fsl_dict = updateParams(fsl_dict,"-thr"," 0.00000001")
    fsl_dict = updateParams(fsl_dict,"-bin",f"{magnitude_biascorr_brain_mask}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{str(phase1)}")
    fsl_dict = updateParams(fsl_dict,"-a","^^^")
    fsl_dict = updateParams(fsl_dict,"-R","^^^")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslstats"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    phasedivstr1 = getLastFromList(runCommand(evaluated_command,UTLOGGER).split("\n"))
    phasediv1 = np.max([abs(float(x)) for x in phasedivstr1.split()]) 

    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{phase2}")
    fsl_dict = updateParams(fsl_dict,"-a","^^^")
    fsl_dict = updateParams(fsl_dict,"-R","^^^")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslstats"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    phasedivstr2 = getLastFromList(runCommand(evaluated_command,UTLOGGER).split("\n"))
    phasediv2 = np.max([abs(float(x)) for x in phasedivstr2.split()]) 

    phaserads1 = newfile(work_dir,phase1,suffix="rads")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{phase1}")
    fsl_dict = updateParams(fsl_dict,"-div",f"{phasediv1}")
    fsl_dict = updateParams(fsl_dict,"-mul","3.14159")
    fsl_dict = updateParams(fsl_dict,"-mas",f"{magnitude_biascorr_brain_mask}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{phaserads1}")
    fsl_dict = updateParams(fsl_dict,"-odt","float")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    phaserads2 = newfile(work_dir,phase2,suffix="rads")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{phase2}")
    fsl_dict = updateParams(fsl_dict,"-div",f"{phasediv2}")
    fsl_dict = updateParams(fsl_dict,"-mul","3.14159")
    fsl_dict = updateParams(fsl_dict,"-mas",f"{magnitude_biascorr_brain_mask}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{phaserads2}")
    fsl_dict = updateParams(fsl_dict,"-odt","float")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    phaserads1_unwrap = newfile(work_dir,phaserads1,suffix="unwrapped")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"-a",f"{magnitude_biascorr}")
    fsl_dict = updateParams(fsl_dict,"-p",f"{phaserads1}")
    fsl_dict = updateParams(fsl_dict,"-m",f"{magnitude_biascorr_brain_mask}")
    fsl_dict = updateParams(fsl_dict,"-u",f"{phaserads1_unwrap}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} prelude"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    phaserads2_unwrap = newfile(work_dir,phaserads2,suffix="unwrapped")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"-a",f"{magnitude_biascorr}")
    fsl_dict = updateParams(fsl_dict,"-p",f"{phaserads2}")
    fsl_dict = updateParams(fsl_dict,"-m",f"{magnitude_biascorr_brain_mask}")
    fsl_dict = updateParams(fsl_dict,"-u",f"{phaserads2_unwrap}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} prelude"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    phasediffrads = newfile(work_dir,phase1,suffix="unwrapped-diff-rads")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{phaserads2_unwrap}")
    fsl_dict = updateParams(fsl_dict,"-sub",f"{phaserads1_unwrap}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{phasediffrads}")
    fsl_dict = updateParams(fsl_dict,"-odt","float")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    fmaprads_raw = newfile(work_dir,phasediffrads,suffix="fmap-raw")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY0",f"{phasediffrads}")
    fsl_dict = updateParams(fsl_dict,"-div",f"{deltaTE}")
    fsl_dict = updateParams(fsl_dict,"DUMMYKEY1",f"{fmaprads_raw}")
    fsl_dict = updateParams(fsl_dict,"-odt","float")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fslmaths"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    fmap = newfile(work_dir,phasediffrads,suffix="fmap-final")
    fsl_dict=OrderedDict()
    fsl_dict = updateParams(fsl_dict,"--loadfmap",f"{fmaprads_raw }")
    fsl_dict = updateParams(fsl_dict,"--mask",f"{magnitude_biascorr_brain_mask}")
    fsl_dict = updateParams(fsl_dict,"--savefmap",f"{fmap}")
    params = get_fslparams(fsl_dict)
    command=f"{command_base} fugue"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,UTLOGGER)

    demean_image(labels_dict,fmap,magnitude_biascorr_brain_mask,os.path.join(work_dir,"tmp1"))
    clean_up_edge(labels_dict,fmap,magnitude_biascorr_brain_mask,os.path.join(work_dir,"tmp2"))

    basil_dict = updateParams(basil_dict,FMAP,fmap)

    echospacing = None
    if os.path.exists(magnitude_biascorr_brain):
        basil_dict = updateParams(basil_dict,FMAPMAG,magnitude_biascorr)
        basil_dict = updateParams(basil_dict,FMAPMAGBRAIN,magnitude_biascorr_brain)
        
        if "EffectiveEchoSpacing" in asljson.keys():
            echospacing = asljson["EffectiveEchoSpacing"]
            IFLOGGER.info(f"Echospacing {echospacing} obtained from BIDS metadata") 
        
        if not echospacing:
            IFLOGGER.info(f"Echospacing not found in BIDS metadata. Attempting to retrieve from config file.") 
            ECHOSPACING_DICT= getParams(labels_dict,"ASL_ECHOSPACING")
            if ECHOSPACING_DICT is not None and isinstance(ECHOSPACING_DICT, dict):
                if asl_acq in ECHOSPACING_DICT.keys():
                    if ECHOSPACING_DICT[asl_acq] is not None and isinstance(ECHOSPACING_DICT[asl_acq], dict):
                        if xnat_project in ECHOSPACING_DICT[asl_acq].keys():
                            echospacing = ECHOSPACING_DICT[asl_acq][xnat_project]

                        elif xnat_shared_project in ECHOSPACING_DICT[asl_acq].keys():
                            echospacing = ECHOSPACING_DICT[asl_acq][xnat_shared_project]
                        
                        elif "default" in ECHOSPACING_DICT[asl_acq].keys():
                            echospacing = ECHOSPACING_DICT[asl_acq]["default"]

                        else:
                            IFLOGGER.info(f"ASL_ECHOSPACING Dictionary keys {ECHOSPACING_DICT[asl_acq].keys()} not valid") 

                    else:
                        echospacing = ECHOSPACING_DICT[asl_acq]
     
            if echospacing:
                IFLOGGER.info(f"Echospacing {echospacing} obtained from config file.")   
            else:
                IFLOGGER.error(f"Echospacing not defined. Fieldmap correction will not work.") 
                raise ValueError("<ASL_ECHOSPACING> not defined in config file for fieldmap processing.")

        basil_dict = updateParams(basil_dict,ECHOSPACING,echospacing) 
        pedir_ijk = asljson["PhaseEncodingDirection"]
        IFLOGGER.info(f"PE Direction of ASL is {pedir_ijk}")   
        pedir_fsl = pedir_ijk.replace('j-','-y').replace('j','y').replace('i-','-x').replace('i','x').replace('k-','-z').replace('k','z')
        IFLOGGER.info(f"PE Direction of ASL converted to {pedir_fsl} for BASIL.")    
        basil_dict = updateParams(basil_dict,PEDIR,pedir_fsl)

    return basil_dict

def basil_proc(labels_dict,bids_dir="",fslanat_dir=""):

    if not bids_dir:
        bids_dir = substitute_labels(labels_dict,"<BIDS_DIR>")

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    command_base, container = getContainer(labels_dict,nodename="basil",SPECIFIC="BASIL_CONTAINER",LOGGER=IFLOGGER)

    IFLOGGER.info("Checking the oxford_asl version:")
    command = f"{command_base} oxford_asl --version"
    evaluated_command=substitute_labels(command, labels_dict)
    runCommand(evaluated_command,IFLOGGER)

    if container:
        IFLOGGER.info("\nChecking the container version:")
        command = f"{command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        runCommand(evaluated_command,IFLOGGER)

    basil_dict={}
    basil_dict = updateParams(basil_dict,MC,IS_PRESENT)
    basil_dict = updateParams(basil_dict,PVCORR,IS_PRESENT)
    basil_dict = updateParams(basil_dict,DEBUG,IS_PRESENT)
    basil_dict = updateParams(basil_dict,REGIONANALYSIS,IS_PRESENT)
    basil_dict = updateParams(basil_dict,FIXBAT,IS_PRESENT)
    basil_dict = updateParams(basil_dict,WHITEPAPER,IS_PRESENT)

    
    output_dir=os.path.join(cwd,"basiloutput")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)
    basil_dict = updateParams(basil_dict,ASL_OUTPUT,output_dir)

    work_dir=os.path.join(output_dir,"basilwork_pan")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir,exist_ok=True)

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')
    participant_project = getParams(labels_dict,"PARTICIPANT_XNAT_PROJECT")

    UM_EXCEPTION = False
    if participant_project == "002_HML":
        part_df = pd.read_csv(os.path.join(bids_dir,"participants.tsv"),sep="\t")
        search_df = part_df[(part_df["participant_id"]=="sub-" + drop_sub(participant_label)) & (part_df["session_id"] == "ses-" + drop_ses(participant_session))]
        if not search_df.empty:
            scantime = search_df.iloc[0]["mri_scan_datetime"]
            if datetime.datetime.strptime(scantime,"%Y-%m-%dT%H:%M:%S.%f%Z") > datetime.datetime(2024,10,21):
                UM_EXCEPTION = True

    if UM_EXCEPTION:
        IFLOGGER.info("Conversion to XA50 software at 002_HML added 1 extra volume to M0 and ASL scans. These have been removed from their BIDS files.")
        #new_bids_dir = os.path.join(output_dir,"bids_dir")
        #copytree(os.path.join(bids_dir,f"sub-{participant_label}"),os.path.join(new_bids_dir,f"sub-{participant_label}"))
        #copy(os.path.join(bids_dir,"participants.tsv"),os.path.join(new_bids_dir,"participants.tsv"))
        #copy(os.path.join(bids_dir,"dataset_description.json"),os.path.join(new_bids_dir,"dataset_description.json"))
        #bids_dir = new_bids_dir
        #process_um_exception(bids_dir, cwd, participant_label, participant_session,labels_dict)

    layout = BIDSLayout(bids_dir)
    asl=layout.get(subject=participant_label,session=participant_session,suffix='asl', extension='nii.gz')

    if len(asl) > 0:
        asl_bidsfile=asl[0]
        asl_file=asl_bidsfile.path

        asljson=asl_bidsfile.get_metadata()
        asl_entities = asl_bidsfile.get_entities()
        if "acquisition" in asl_entities.keys():
            asl_acq = "acq-" + asl_entities["acquisition"]
        else:
            asl_acq = get_bidstag("acq",asl_bidsfile.filename)
        
        if not asl_acq:
            asl_acq = "default"

        asl_type="PCASL"
        if "ArterialSpinLabelingType" in asljson.keys():
            asl_type = asljson["ArterialSpinLabelingType"]

        m0_type="Separate"
        if "M0Type" in asljson.keys():
            m0_type = asljson["M0Type"]

        basil_dict = updateParams(basil_dict,IAF,"tc")
        ASLCONTEXT = getParams(labels_dict,"ASLCONTEXT")
        if ASLCONTEXT and isinstance(ASLCONTEXT,dict):
            if asl_acq in ASLCONTEXT.keys():
                if ASLCONTEXT[asl_acq] == "control:label":
                    basil_dict = updateParams(basil_dict,IAF,"ct")
                elif ASLCONTEXT[asl_acq] == "label:control":
                    basil_dict = updateParams(basil_dict,IAF,"tc")
                elif ASLCONTEXT[asl_acq] == "m0scan:control:label":
                    basil_dict = updateParams(basil_dict,IAF,"ct")
                    asl_file,m0_file = splitASL(asl_file,command_base,work_dir,labels_dict)

        asl_scaling = None
        ASL_SCALING_DICT = getParams(labels_dict,'ASL_SCALING')
        if ASL_SCALING_DICT  and isinstance(ASL_SCALING_DICT,dict):
            if asl_acq in ASL_SCALING_DICT.keys():
                asl_scaling = substitute_labels(ASL_SCALING_DICT[asl_acq],labels_dict)

        if asl_scaling:
            basil_dict = scaleASL(asl_file, command_base,asl_scaling, work_dir, basil_dict,labels_dict)
        else:
            basil_dict = updateParams(basil_dict,ASL_INPUT,asl_file)

        asl_img = nb.load(asl_file)
        rpts=int(asl_img.header["dim"][4]/2)
        basil_dict = updateParams(basil_dict,IBF,'rpt')
        basil_dict = updateParams(basil_dict,RPTS,str(rpts))

        fix_bolus=None
        if "BolusCutOffTechnique" in asljson.keys():
            fix_bolus = asljson["BolusCutOffTechnique"]

        if fix_bolus  is not None:
            basil_dict = updateParams(basil_dict,FIXBOLUS,IS_PRESENT)

        pld = None
        labelDuration=None
        if "PostLabelingDelay" in asljson.keys():
            pld = asljson["PostLabelingDelay"]
        if "LabelingDuration" in asljson.keys():
            labelDuration = asljson["LabelingDuration"]

        if labelDuration is not None:
            basil_dict = updateParams(basil_dict,BOLUS,str(labelDuration))

        if asl_type == "PCASL" or asl_type == "CASL":
            basil_dict = updateParams(basil_dict,CASL,IS_PRESENT)
            if labelDuration is not None and pld is not None:
                tis = pld + labelDuration
                basil_dict = updateParams(basil_dict,TIS,str(tis))
        else:
            # PLD in PASL json is actually the TIS
            if labelDuration is not None and pld is not None:
                tis = pld
                basil_dict = updateParams(basil_dict,TIS,str(tis))

        # process field map if it exists
        FIELDMAP_TYPE_DICT = getParams(labels_dict,'FIELDMAP_TYPE')
        fieldmap_type = FIELDMAP_TYPE_DICT 
        if FIELDMAP_TYPE_DICT  is not None and isinstance(FIELDMAP_TYPE_DICT,dict):
            if asl_acq in FIELDMAP_TYPE_DICT.keys():
                fieldmap_type = substitute_labels(FIELDMAP_TYPE_DICT[asl_acq],labels_dict)

        if fieldmap_type:
            # use preprocessed field mao from fmriprep
            if fieldmap_type == "fmriprep_preproc":
                FMRIPREP_FIELDMAP_DIR_DICT  = getParams(labels_dict,'FMRIPREP_FIELDMAP_DIR')
                fmriprep_fieldmap_dir = FMRIPREP_FIELDMAP_DIR_DICT
                if FMRIPREP_FIELDMAP_DIR_DICT is not None and isinstance(FMRIPREP_FIELDMAP_DIR_DICT ,dict):
                    if asl_acq in FMRIPREP_FIELDMAP_DIR_DICT.keys():
                        fmriprep_fieldmap_dir = substitute_labels(FMRIPREP_FIELDMAP_DIR_DICT[asl_acq],labels_dict)

                if fmriprep_fieldmap_dir and os.path.exists(fmriprep_fieldmap_dir):
                    basil_dict = process_fmriprep_fieldmap(fmriprep_fieldmap_dir,layout, asljson , asl_acq, basil_dict, labels_dict, command_base, work_dir)
                else:
                    IFLOGGER.warn(f"Attempting to create fieldmap using {fieldmap_type} but sources not found. Exiting")
                    sys.exit(1)
            elif fieldmap_type == "sdcflows_preproc":
                SDCFLOWS_FIELDMAP_DIR_DICT  = getParams(labels_dict,'SDCFLOWS_FIELDMAP_DIR')
                fieldmap_dir =  SDCFLOWS_FIELDMAP_DIR_DICT
                if SDCFLOWS_FIELDMAP_DIR_DICT is not None and isinstance(SDCFLOWS_FIELDMAP_DIR_DICT ,dict):
                    if asl_acq in SDCFLOWS_FIELDMAP_DIR_DICT.keys():
                        fieldmap_dir = substitute_labels(SDCFLOWS_FIELDMAP_DIR_DICT[asl_acq],labels_dict)

                SDCFLOWS_FMAP_MODE = getParams(labels_dict,"SDCFLOWS_FIELDMAP_MODE") 
                if SDCFLOWS_FMAP_MODE:
                    sdcflows_fmap_mode = SDCFLOWS_FMAP_MODE
                else:
                    sdcflows_fmap_mode="phasediff"
                    labels_dict = updateParams(labels_dict,"SDCFLOWS_FIELDMAP_MODE",sdcflows_fmap_mode)

                if fieldmap_dir and os.path.exists(fieldmap_dir):
                    basil_dict = process_sdcflows_fieldmap(fieldmap_dir,layout, asljson , asl_acq, basil_dict, labels_dict, command_base, work_dir,bids_dir=bids_dir,subject=participant_label,session=participant_session, fmap_mode=sdcflows_fmap_mode)
                else:
                    IFLOGGER.warn(f"Attempting to create fieldmap using {fieldmap_type} but sources not found. Exiting")
                    sys.exit(1)
            elif fieldmap_type == "fsl_prepare_fieldmap":            
                basil_dict = process_fsl_prepare_fieldmap(layout, asljson,basil_dict,labels_dict, asljson, asl_acq, command_base, work_dir)

        fslanat_dir=os.path.abspath(fslanat_dir)
        basil_dict = updateParams(basil_dict,FSLANAT,fslanat_dir)


        CMETHOD_OPTS = getParams(labels_dict,"CMETHOD_OPTS")
        if CMETHOD_OPTS is not None and isinstance(CMETHOD_OPTS,dict):
            if asl_acq in CMETHOD_OPTS.keys():
                basil_dict = updateParams(basil_dict,CMETHOD,CMETHOD_OPTS[asl_acq])

        if m0_type == "Separate":
            m0_entities = asl_entities.copy()
            m0_entities["suffix"]="m0scan"
            m0  = layout.get(return_type='file', invalid_filters='allow', **m0_entities)
            if len(m0) > 0:
                m0_file=m0[0]
                basil_dict = updateParams(basil_dict,CALIBRATION,m0_file)
                m0_md = layout.get(**m0_entities)[0].get_metadata()
                if "RepetitionTime" in m0_md.keys():
                    basil_dict = updateParams(basil_dict,TR,str(m0_md["RepetitionTime"]))
                else:
                    IFLOGGER.warn("RepetitionTime not found for m0. Default of 5s will be used by BASIL.")
        elif m0_type == "Included" and m0_file:
            IFLOGGER.info(f"M0 defined as included and defined at {m0_file}.")
            basil_dict = updateParams(basil_dict,CALIBRATION,m0_file)
            if "RepetitionTime" in asljson.keys():
                basil_dict = updateParams(basil_dict,TR,str(asljson["RepetitionTime"]))
            else:
                IFLOGGER.warn("RepetitionTime not found for m0. Default of 5s will be used by BASIL.")

        
        else:
            IFLOGGER.info(f"M0 Type {m0_type} not recognized. Expecting Separate or Included. Check spelling and case.")


        # Additional params
        BASIL_OVERRIDE_PARAMS = getParams(labels_dict,"BASIL_OVERRIDE_PARAMS")
        if BASIL_OVERRIDE_PARAMS and isinstance(BASIL_OVERRIDE_PARAMS,dict):
            add_labels(BASIL_OVERRIDE_PARAMS,basil_dict) 

        # Additional params for specific subjects
        UNIQUE_BASIL_OVERRIDE_PARAMS = getParams(labels_dict,"UNIQUE_BASIL_OVERRIDE_PARAMS")
        if UNIQUE_BASIL_OVERRIDE_PARAMS and isinstance(UNIQUE_BASIL_OVERRIDE_PARAMS,dict):
            for itemkey,itemvalue in UNIQUE_BASIL_OVERRIDE_PARAMS.items():
                if itemkey == f"{participant_label}_{participant_session}" or itemkey == f"{participant_label}" and isinstance(itemvalue,dict):
                    add_labels(itemvalue,basil_dict)    

        params = ""
        for basil_tag, basil_value in basil_dict.items():
            if "--" in basil_tag and "---" not in basil_tag:
                if basil_value == IS_PRESENT:
                    params=params + " " + basil_tag
                elif basil_value == IGNORE:
                    IFLOGGER.info(f"Parameter {basil_tag} is being skipped. This has been explicitly required in configuration.")
                else:
                    params = params + " " + basil_tag+"=" + str(basil_value)

            elif "-" in basil_tag and "--" not in basil_tag:
                params = params + " " + basil_tag + " " + str(basil_value)

            else:
                print(f"Basil tag {basil_tag} not valid.")


        command=f"{command_base} oxford_asl"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        runCommand(evaluated_command,IFLOGGER)
    else:
        IFLOGGER.warn(f"ASL acquisition not found for subject {participant_label} and session {participant_session}")


    cbf_native = getGlob(os.path.join(output_dir,"native_space","perfusion_calib.nii.gz"))
    cbf_t1 = getGlob(os.path.join(output_dir,"struct_space","perfusion_calib.nii.gz"))
    cbf_mni6 = getGlob(os.path.join(output_dir,"std_space","perfusion_calib.nii.gz"))
    out_files=[]
    out_files.insert(0,cbf_native)
    out_files.insert(1,cbf_t1)
    out_files.insert(2,cbf_mni6)


    return {
        "cbf_native":cbf_native,
        "cbf_t1":cbf_t1,
        "cbf_mni6":cbf_mni6,
        "output_dir":output_dir,
        "out_files":out_files
    }



class basilInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)
    fslanat_dir = traits.String("",desc="FSLANAT Directory", usedefault=True)

class basilOutputSpec(TraitedSpec):
    cbf_native = File(desc='cbf_native')
    cbf_t1 = File(desc='cbf_t1')
    cbf_mni6 = File(desc='cbf_mni6')    
    output_dir = traits.String(desc="output directory of basil output")
    out_files = traits.List(desc='list of files')
    
class basil_pan(BaseInterface):
    input_spec = basilInputSpec
    output_spec = basilOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = basil_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir,
            self.inputs.fslanat_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="basil_node",bids_dir="",fslanat_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(basil_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir
    pan_node.inputs.fslanat_dir =  fslanat_dir

    return pan_node


