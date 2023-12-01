from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def fmriprep_proc(labels_dict,bids_dir=""):


    container_run_options = getParams(labels_dict,'CONTAINER_RUN_OPTIONS')
    if not container_run_options:
        container_run_options = ""

    container_prerun = getParams(labels_dict,'CONTAINER_PRERUN')
    if not container_prerun:
        container_prerun = ""

    container = getParams(labels_dict,'CONTAINER')
    if not container:
        container = getParams(labels_dict,'FMRIPREP_CONTAINER')
        if not container:
            container = getParams(labels_dict,'NEURO_CONTAINER')
            if not container:
                IFLOGGER.info("Container not defined for FMRIprep pipeline. Qsiprep should be accessible on local path for pipeline to succeed")
                if container_run_options:
                    IFLOGGER.info("Note that '{container_run_options}' set as run options for non-existing container. This may cause the pipeline to fail.")
                
                if container_prerun:
                    IFLOGGER.info("Note that '{container_prerun}' set as pre-run options for non-existing container. This may cause the pipeline to fail.")

    command_base = f"{container_run_options} {container} {container_prerun}"
    if container:
        IFLOGGER.info("Checking the fmriprep version:")
        command = f"{command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    cwd=os.getcwd()
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    params="--participant_label <PARTICIPANT_LABEL>" \
        " --output-spaces MNI152NLin6Asym:res-1 MNI152NLin2009cAsym:res-1 fsLR fsaverage anat func"\
        " --skip-bids-validation"\
        " --mem_mb <BIDSAPP_MEMORY>" \
        " --cifti-output"\
        " --nthreads <BIDSAPP_THREADS>"\
        " --fs-license-file <FSLICENSE>"\
        " --omp-nthreads <BIDSAPP_THREADS>"\
        " -w " + cwd + "/fmriwork"

    command=f"{command_base}"\
            " "+ bids_dir +\
            " "+ cwd +"/fmrioutput"\
            " participant"\
            " "+ params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

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


