from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging
import json

IFLOGGER=nlogging.getLogger('nipype.interface')

IS_PRESENT="^^^"
IGNORE="###"

def qsiprep_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    command_base, container = getContainer(labels_dict,nodename="qsiprep", SPECIFIC="QSIPREP_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the qsiprep version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    eddy_config = getParams(labels_dict,'EDDY_CONFIG')
    eddy_json=""
    if eddy_config:
        if os.path.exists(eddy_config):
            with open(eddy_config, 'r') as infile:
                eddy_json = json.load(infile)
        if eddy_json:
            IFLOGGER.info(f"eddy params provided in file {eddy_config} and contents are:")
            IFLOGGER.info(f"{eddy_json}")

    qsiprep_dict={}
    qsiprep_dict = updateParams(qsiprep_dict,"--participant_label","<PARTICIPANT_LABEL>")
    qsiprep_dict = updateParams(qsiprep_dict,"--separate-all-dwis",IS_PRESENT)
    qsiprep_dict = updateParams(qsiprep_dict,"--skip-bids-validation",IS_PRESENT)
    qsiprep_dict = updateParams(qsiprep_dict,"--hmc-model" ,"eddy")
    qsiprep_dict = updateParams(qsiprep_dict,"--unringing-method" ,"rpg")
    qsiprep_dict = updateParams(qsiprep_dict,"--eddy-config" ,"<EDDY_CONFIG>")
    qsiprep_dict = updateParams(qsiprep_dict,"--mem_mb","<BIDSAPP_MEMORY>")
    qsiprep_dict = updateParams(qsiprep_dict,"--nthreads","<BIDSAPP_THREADS>")
    qsiprep_dict = updateParams(qsiprep_dict,"--fs-license-file","<FSLICENSE>")
    qsiprep_dict = updateParams(qsiprep_dict,"--write-graph",IS_PRESENT)
    qsiprep_dict = updateParams(qsiprep_dict,"--output-resolution","<OUTPUT_RES>")
    qsiprep_dict = updateParams(qsiprep_dict,"-w","<CWD>/qsiprep_work")


    # Additional params
    QSIPREP_OVERRIDE_PARAMS = getParams(labels_dict,"QSIPREP_OVERRIDE_PARAMS")
    if QSIPREP_OVERRIDE_PARAMS and isinstance(QSIPREP_OVERRIDE_PARAMS,dict):
        add_labels(QSIPREP_OVERRIDE_PARAMS,qsiprep_dict)        

    params = ""
    for qsiprep_tag, qsiprep_value in qsiprep_dict.items():
        if "--" in qsiprep_tag and "---" not in qsiprep_tag:
            if qsiprep_value == IS_PRESENT:
                params=params + " " + qsiprep_tag
            elif qsiprep_value == IGNORE:
                IFLOGGER.info(f"Parameter {qsiprep_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                # we dont need = sign for qsiprep just for basi;
                params = params + " " + qsiprep_tag + " " + qsiprep_value

        elif "-" in qsiprep_tag and "--" not in qsiprep_tag:
            params = params + " " + qsiprep_tag + " " + qsiprep_value

        else:
            print(f"qsiprep tag {qsiprep_tag} not valid.") 


    command=f"{command_base}"\
            " "+bids_dir +\
            " <CWD>"\
            " participant"\
            " " + params

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

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



class qsiprepInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class qsiprepOutputSpec(TraitedSpec):
    dwi_preprocess = File(desc='Preprocessed DWI')
    mat_t12mni = File(desc='T1 to MNI transform')
    mat_mni2t1 = File(desc='MNI to T1 transform')
    mniref = File(desc='MNI reference')
    t1ref = File(desc='T1 reference')
    output_dir = traits.String(desc="QSIPREP output directory")
    out_files = traits.List(desc='list of files')
    
class qsiprep_pan(BaseInterface):
    input_spec = qsiprepInputSpec
    output_spec = qsiprepOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = qsiprep_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='qsiprep_node',bids_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(qsiprep_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


