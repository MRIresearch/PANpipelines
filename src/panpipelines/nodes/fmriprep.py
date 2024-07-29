from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging
from bids import BIDSLayout

IFLOGGER=nlogging.getLogger('nipype.interface')

IS_PRESENT="^^^"
IGNORE="###"

def fmriprep_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    command_base, container = getContainer(labels_dict,nodename="fmriprep", SPECIFIC="FMRIPREP_CONTAINER",LOGGER=IFLOGGER)
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)

    IFLOGGER.info("Checking the fmriprep version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    # handle field maps - use dwirpe as standard if valid, otherwise use megre 
    if not bids_dir:
        bids_dir = substitute_labels('<BIDS_DIR>', labels_dict)
    layout = BIDSLayout(bids_dir)

    fmri_fmap_entity ={}
    fmri_fmap_entity["extension"] = "nii.gz"
    fmri_fmap_entity["datatype"]="fmap"
    fmri_fmap_entity["acquisition"]="fmri"
    fmri_fmap_entity["session"]=participant_session
    fmri_fmap = layout.get(return_type='file', invalid_filters="allow", **fmri_fmap_entity)

    bids_filter_dict={}
    bids_filter_dict["bold"] = {}
    bids_filter_dict["bold"]["session"] =  participant_session
    bids_filter_dict["fmap"] = {}
    bids_filter_dict["fmap"]["session"] =  participant_session

    use_megre_fmap = getParams(labels_dict,'USE_MEGRE_FMAP')
    if use_megre_fmap and participant_label in use_megre_fmap:
        bids_filter_dict["fmap"]["suffix"] =  ["phase1","phase2","magnitude1","magnitude2"]
    elif use_megre_fmap and f"{participant_label}_{participant_session}" in use_megre_fmap:
        bids_filter_dict["fmap"]["suffix"] =  ["phase1","phase2","magnitude1","magnitude2"]
    elif fmri_fmap:
        bids_filter_dict["fmap"]["acquisition"] =  "fmri"
    else:
        bids_filter_dict["fmap"]["suffix"] =  ["phase1","phase2","magnitude1","magnitude2"]

    bids_filter_file = os.path.join(cwd,f"{participant_label}_{participant_session}_bids_filter_file.json")
    export_labels(bids_filter_dict,bids_filter_file)
    IFLOGGER.info(f"Specifying session filter: exporting {bids_filter_dict} to {bids_filter_file}")

    fmriprep_dict={}
    fmriprep_dict = updateParams(fmriprep_dict,"--participant_label","<PARTICIPANT_LABEL>")
    fmriprep_dict = updateParams(fmriprep_dict,"--output-spaces","MNI152NLin6Asym:res-2 MNI152NLin2009cAsym:res-2")
    fmriprep_dict = updateParams(fmriprep_dict,"--skip-bids-validation",IS_PRESENT)
    fmriprep_dict = updateParams(fmriprep_dict,"--bids-filter-file",bids_filter_file)
    fmriprep_dict = updateParams(fmriprep_dict,"--mem_mb","<BIDSAPP_MEMORY>")
    fmriprep_dict = updateParams(fmriprep_dict,"--nthreads","<BIDSAPP_THREADS>")
    fmriprep_dict = updateParams(fmriprep_dict,"--fs-license-file","<FSLICENSE>")
    fmriprep_dict = updateParams(fmriprep_dict,"--omp-nthreads","1")
    fmriprep_dict = updateParams(fmriprep_dict,"-w","<CWD>/fmriwork")

    # Additional params
    FMRIPREP_OVERRIDE_PARAMS = getParams(labels_dict,"FMRIPREP_OVERRIDE_PARAMS")
    if FMRIPREP_OVERRIDE_PARAMS and isinstance(FMRIPREP_OVERRIDE_PARAMS,dict):
        add_labels(FMRIPREP_OVERRIDE_PARAMS,fmriprep_dict)        

    params = ""
    for fmriprep_tag, fmriprep_value in fmriprep_dict.items():
        if "--" in fmriprep_tag and "---" not in fmriprep_tag:
            if fmriprep_value == IS_PRESENT:
                params=params + " " + fmriprep_tag
            elif fmriprep_value == IGNORE:
                IFLOGGER.info(f"Parameter {fmriprep_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                # we dont need = sign for fmriprep just for basi;
                params = params + " " + fmriprep_tag + " " + fmriprep_value

        elif "-" in fmriprep_tag and "--" not in fmriprep_tag:
            params = params + " " + fmriprep_tag + " " + fmriprep_value

        else:
            print(f"fmriprep tag {fmriprep_tag} not valid.")

    command=f"{command_base}"\
            " "+ bids_dir +\
            " <CWD>/fmrioutput"\
            " participant"\
            " "+ params 

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    fmri_preprocess_mnilin6 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','func','*space-MNI152NLin6Asym*preproc_bold.nii.gz'))
    fmri_preprocess_mni2009 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','func','*space-MNI152NLin2009cAsym*preproc_bold.nii.gz'))
    mat_t1_mnilin6 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*from-T1w*MNI152NLin6*mode-image_xfm.h5'))
    mat_t1_mni2009 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*from-T1w*MNI152NLin2009*mode-image_xfm.h5'))
    mat_t1_func = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','func','*to-scanner*mode-image_xfm.txt'))
    mat_mnilin6_t1 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*from-MNI152NLin6*mode-image_xfm.h5'))
    mat_mni2009_t1 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*from-MNI152NLin2009*mode-image_xfm.h5'))
    mat_func_t1 = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','func','*from-scanner*mode-image_xfm.txt'))
    confounds = getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','func','*timeseries*.tsv'))
    mnilin6ref =  getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*{}*MNI152NLin6*desc-preproc_T1w.nii.gz'.format(participant_label)))
    mni2009ref =  getGlob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*{}*MNI152NLin2009*desc-preproc_T1w.nii.gz'.format(participant_label)))

    t1ref =  glob.glob(os.path.join(cwd,'fmrioutput','fmriprep','sub-{}'.format(participant_label),'ses-*','anat','*{}*desc-preproc_T1w.nii.gz'.format(participant_label)))
    t1ref = getFirstFromList([ s for s in t1ref if "MNI" not in s])

    output_dir = cwd

    out_files=[]
    out_files.insert(0,fmri_preprocess_mnilin6)
    out_files.insert(1,fmri_preprocess_mni2009)
    out_files.insert(2,mat_t1_mnilin6)
    out_files.insert(3,mat_t1_mni2009)
    out_files.insert(4,mat_t1_func)
    out_files.insert(5,mat_mnilin6_t1)
    out_files.insert(6,mat_mni2009_t1)
    out_files.insert(7,mat_func_t1)
    out_files.insert(8,confounds)
    out_files.insert(9,t1ref)
    out_files.insert(10,mnilin6ref)
    out_files.insert(11,mni2009ref)


    return {
        "fmri_preprocess_mnilin6":fmri_preprocess_mnilin6,
        "fmri_preprocess_mni2009":fmri_preprocess_mni2009,
        "mat_t1_mnilin6":mat_t1_mnilin6,
        "mat_t1_mni2009":mat_t1_mni2009,
        "mat_t1_func":mat_t1_func,
        "mat_mnilin6_t1":mat_mnilin6_t1,
        "mat_mni2009_t1":mat_mni2009_t1,
        "mat_func_t1":mat_func_t1,
        "confounds":confounds,
        "t1ref":t1ref,
        "mnilin6ref":mnilin6ref,
        "mni2009ref":mni2009ref,
        "output_dir":output_dir,
        "out_files":out_files
    }



class fmriprepInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class fmriprepOutputSpec(TraitedSpec):
    fmri_preprocess_mnilin6 = File(desc='Preprocessed DWI MNILin6 space')
    fmri_preprocess_mni2009 = File(desc='Preprocessed DWI MNILin2009 space')
    mat_t1_mnilin6 = File(desc='T1 to MNILin6 transform')
    mat_t1_mni2009 = File(desc='T1 to MNI2009 transform')
    mat_t1_func = File(desc="T1 to Functional transform")
    mat_mnilin6_t1 = File(desc='MNILin6 to T1 transform')
    mat_mni2009_t1 = File(desc='MNI2009 to T1 transform')
    mat_func_t1 = File(desc="Functional to T1 transform")
    confounds = File(desc="fmriprep calculated confounds")
    t1ref = File(desc='T1 reference')
    mnilin6ref = File(desc='MNILin6 reference')
    mni2009ref = File(desc='MNI2009 reference')
    output_dir = traits.String(desc="FMRIPREP output directory")
    out_files = traits.List(desc='list of files')
    
class fmriprep_pan(BaseInterface):
    input_spec = fmriprepInputSpec
    output_spec = fmriprepOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = fmriprep_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='fmriprep_node',bids_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(fmriprep_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


