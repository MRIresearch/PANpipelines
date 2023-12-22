from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def dummy_proc(labels_dict,bids_dir=""):

    DEBUG=True

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)


    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    command_base, container = getContainer(labels_dict,nodename="qsiprep", SPECIFIC="QSIPREP_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the qsiprep version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    params="--participant_label <PARTICIPANT_LABEL>" \
        " --separate-all-dwis"\
        " --hmc-model eddy"\
        " --eddy-config <EDDY_CONFIG>" \
        " --unringing-method mrdegibbs" \
        " --mem_mb <BIDSAPP_MEMORY>" \
        " --nthreads <BIDSAPP_THREADS>"\
        " --fs-license-file <FSLICENSE>"\
        " --skip-bids-validation"\
        " -w <CWD>/qsiprep_work"\
        " --write-graph"\
        " --output-resolution <OUTPUT_RES>"

    command=f"{command_base}"\
            " "+bids_dir +\
            " <CWD>"\
            " participant"\
            " "+params


    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    IFLOGGER.info(evaluated_command_args)

    if not DEBUG:
        results = subprocess.run(evaluated_command_args)
        IFLOGGER.info(results.stdout)

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    dwi_preprocess = getGlob(os.path.join(cwd,'qsiprep','sub-{}'.format(participant_label),'ses-*','dwi','*preproc_dwi.nii.gz'))
    mat_t12mni = getGlob(os.path.join(cwd,'qsiprep','sub-{}'.format(participant_label),'anat','*from-T1w*mode-image_xfm.h5'))
    mat_mni2t1 = getGlob(os.path.join(cwd,'qsiprep','sub-{}'.format(participant_label),'anat','*from-MNI*mode-image_xfm.h5'))
    t1ref =  getGlob(os.path.join(cwd,'qsiprep','sub-{}'.format(participant_label),'anat','*{}_desc-preproc_T1w.nii.gz'.format(participant_label)))
    mniref =  getGlob(os.path.join(cwd,'qsiprep','sub-{}'.format(participant_label),'anat','*{}*MNI*desc-preproc_T1w.nii.gz'.format(participant_label)))
    output_dir = cwd

    
    out_files=[]
    out_files.insert(0,dwi_preprocess)
    out_files.insert(1,mat_t12mni)
    out_files.insert(2,mat_mni2t1)
    out_files.insert(3,mniref)
    out_files.insert(4,t1ref)


    return {
        "dwi_preprocess":dwi_preprocess,
        "mat_t12mni":mat_t12mni,
        "mat_mni2t1":mat_mni2t1,
        "mniref":mniref,
        "t1ref":t1ref,
        "output_dir":output_dir,
        "out_files":out_files
    }



class dummyInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class dummyOutputSpec(TraitedSpec):
    dwi_preprocess = File(desc='Preprocessed DWI')
    mat_t12mni = File(desc='T1 to MNI transform')
    mat_mni2t1 = File(desc='MNI to T1 transform')
    mniref = File(desc='MNI reference')
    t1ref = File(desc='T1 reference')
    output_dir = traits.String(desc="QSIPREP output directory")
    out_files = traits.List(desc='list of files')
    
class dummy_pan(BaseInterface):
    input_spec = dummyInputSpec
    output_spec = dummyOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = dummy_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='dummy_node',bids_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(dummy_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


