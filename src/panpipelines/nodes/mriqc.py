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

def mriqc_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    command_base, container = getContainer(labels_dict,nodename="mriqc", SPECIFIC="MRIQC_CONTAINER",LOGGER=IFLOGGER)
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)

    IFLOGGER.info("Checking the mriqc version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    # handle field maps - use dwirpe as standard if valid, otherwise use megre
    if not bids_dir:
        bids_dir = substitute_labels('<BIDS_DIR>', labels_dict)
    layout = BIDSLayout(bids_dir)

    bids_filter_dict={}
    bids_filter_dict["bold"] = {}
    bids_filter_dict["bold"]["session"] =  participant_session
    bids_filter_dict["dwi"] = {}
    bids_filter_dict["dwi"]["session"] =  participant_session
    bids_filter_dict["t1w"] = {}
    bids_filter_dict["t1w"]["session"] =  participant_session
    bids_filter_dict["t2w"] = {}
    bids_filter_dict["t2w"]["session"] =  participant_session

    bids_filter_file = os.path.join(cwd,f"{participant_label}_{participant_session}_bids_filter_file.json")
    export_labels(bids_filter_dict,bids_filter_file)
    IFLOGGER.info(f"Specifying session filter: exporting {bids_filter_dict} to {bids_filter_file}")

    mriqc_dict={}
    mriqc_dict = updateParams(mriqc_dict,"--participant_label","<PARTICIPANT_LABEL>")
    mriqc_dict = updateParams(mriqc_dict,"--bids-filter-file",bids_filter_file)
    mriqc_dict = updateParams(mriqc_dict,"--mem","<BIDSAPP_MEMORY>")
    mriqc_dict = updateParams(mriqc_dict,"--nprocs","<BIDSAPP_THREADS>")
    mriqc_dict = updateParams(mriqc_dict,"--omp-nthreads","4")
    mriqc_dict = updateParams(mriqc_dict,"--no-sub",IS_PRESENT)
    mriqc_dict = updateParams(mriqc_dict,"-w","<CWD>/mriqcwork")

    # Additional params
    MRIQC_OVERRIDE_PARAMS = getParams(labels_dict,"MRIQC_OVERRIDE_PARAMS")
    if MRIQC_OVERRIDE_PARAMS and isinstance(MRIQC_OVERRIDE_PARAMS,dict):
        add_labels(MRIQC_OVERRIDE_PARAMS,mriqc_dict)

    # Additional params for specific subjects
    UNIQUE_MRIQC_OVERRIDE_PARAMS = getParams(labels_dict,"UNIQUE_MRIQC_OVERRIDE_PARAMS")
    if UNIQUE_MRIQC_OVERRIDE_PARAMS and isinstance(UNIQUE_MRIQC_OVERRIDE_PARAMS,list):
        for override_definition in UNIQUE_MRIQC_OVERRIDE_PARAMS:
            if isinstance(override_definition,dict) and "CANDIDATES" in override_definition.keys() and "PARAMS" in override_definition.keys():
                subject_list = override_definition["CANDIDATES"]
                subject_params = override_definition["PARAMS"]
                if f"{participant_label}_{participant_session}" in subject_list or f"{participant_label}" in subject_list:
                    add_labels(subject_params,mriqc_dict)        

    params = ""
    for mriqc_tag, mriqc_value in mriqc_dict.items():
        if "--" in mriqc_tag and "---" not in mriqc_tag:
            if mriqc_value == IS_PRESENT:
                params=params + " " + mriqc_tag
            elif mriqc_value == IGNORE:
                IFLOGGER.info(f"Parameter {mriqc_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                # we dont need = sign for mriqc just for basi;
                params = params + " " + mriqc_tag + " " + mriqc_value

        elif "-" in mriqc_tag and "--" not in mriqc_tag:
            params = params + " " + mriqc_tag + " " + mriqc_value

        else:
            print(f"mriqc tag {mriqc_tag} not valid.")

    command=f"{command_base}"\
            " "+ bids_dir +\
            " <CWD>/mriqcout"\
            " participant"\
            " "+ params 

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    bold_rep = getGlob(os.path.join(cwd,'mriqcoutput','sub-{}'.format(participant_label),'ses-*','func','*bold.json'))
    t1w_rep = getGlob(os.path.join(cwd,'mriqcoutput','sub-{}'.format(participant_label),'ses-*','anat','*T1w.json'))
    t2w_rep= getGlob(os.path.join(cwd,'mriqcoutput','sub-{}'.format(participant_label),'ses-*','anat','*T2w.json'))
    dwi_rep = getGlob(os.path.join(cwd,'mriqcoutput','sub-{}'.format(participant_label),'ses-*','dwi','*dwi.json'))

    output_dir = cwd

    out_files=[]
    if bold_rep:
        out_files.insert(0,bold_rep)
    if t1w_rep:
        out_files.insert(0,t1w_rep)
    if t2w_rep:
        out_files.insert(0,t2w_rep)
    if dwi_rep:
        out_files.insert(0,dwi_rep)


    return {
        "output_dir":output_dir,
        "out_files":out_files
    }



class mriqcInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class mriqcOutputSpec(TraitedSpec):
    output_dir = traits.String(desc="MRIQC output directory")
    out_files = traits.List(desc='list of files')
    
class mriqc_pan(BaseInterface):
    input_spec = mriqcInputSpec
    output_spec = mriqcOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = mriqc_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='mriqc_node',bids_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(mriqc_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


