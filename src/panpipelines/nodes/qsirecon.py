from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

IS_PRESENT="^^^"
IGNORE="###"

def qsirecon_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    command_base, container = getContainer(labels_dict,nodename="qsirecon", SPECIFIC="QSIRECON_CONTAINER",LOGGER=IFLOGGER)

    qsirecon_outdir=getParams(labels_dict,"QSIRECON_OUTDIR")
    if not qsirecon_outdir:
        qsirecon_outdir=f"{cwd}"
        updateParams(labels_dict,"QSIRECON_OUTDIR",qsirecon_outdir)
    else:
        qsirecon_outdir=substitute_labels(qsirecon_outdir,labels_dict)
        os.makedirs(qsirecon_outdir,exist_ok=True)

    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)
    
    IFLOGGER.info("Checking the qsirecon version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    input_dir=substitute_labels(input_dir,labels_dict)

    # set up dwi to process just the specific dwi session
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    bids_filter_dict={}
    bids_filter_dict["dwi"] = {}
    bids_filter_dict["dwi"]["session"] =  participant_session
    bids_filter_file = os.path.join(cwd,f"{participant_label}_{participant_session}_bids_filter_file.json")
    export_labels(bids_filter_dict,bids_filter_file)
    IFLOGGER.info(f"Specifying session filter: exporting {bids_filter_dict} to {bids_filter_file}")

    qsirecon_dict={}
    qsirecon_dict = updateParams(qsirecon_dict,"--participant-label","<PARTICIPANT_LABEL>")
    qsirecon_dict = updateParams(qsirecon_dict,"--recon-spec","<RECON_TYPE>")
    qsirecon_dict = updateParams(qsirecon_dict,"--bids-filter-file",bids_filter_file)
    qsirecon_dict = updateParams(qsirecon_dict,"--mem","<BIDSAPP_MEMORY>")
    qsirecon_dict = updateParams(qsirecon_dict,"--nthreads","<BIDSAPP_THREADS>")
    qsirecon_dict = updateParams(qsirecon_dict,"--fs-license-file","<FSLICENSE>")
    qsirecon_dict = updateParams(qsirecon_dict,"--skip-odf-report",IS_PRESENT)
    qsirecon_dict = updateParams(qsirecon_dict,"--output-resolution","<OUTPUT_RES>")
    qsirecon_dict = updateParams(qsirecon_dict,"-w","<CWD>/qsirecon_work")

    # Additional params
    QSIRECON_OVERRIDE_PARAMS = getParams(labels_dict,"QSIRECON_OVERRIDE_PARAMS")
    if QSIRECON_OVERRIDE_PARAMS and isinstance(QSIRECON_OVERRIDE_PARAMS,dict):
        add_labels(QSIRECON_OVERRIDE_PARAMS,qsirecon_dict)        

    params = ""
    for qsirecon_tag, qsirecon_value in qsirecon_dict.items():
        if "--" in qsirecon_tag and "---" not in qsirecon_tag:
            if qsirecon_value == IS_PRESENT:
                params=params + " " + qsirecon_tag
            elif qsirecon_value == IGNORE:
                IFLOGGER.info(f"Parameter {qsirecon_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                # we dont need = sign for qsirecon just for basi;
                params = params + " " + qsirecon_tag + " " + qsirecon_value

        elif "-" in qsirecon_tag and "--" not in qsirecon_tag:
            params = params + " " + qsirecon_tag + " " + qsirecon_value

        else:
            print(f"qsirecon tag {qsirecon_tag} not valid.") 

    command=f"{command_base}"\
            f" {input_dir}"\
            f" {qsirecon_outdir}"\
            " participant"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    output_dir = cwd

    
    return {
        "output_dir":output_dir,
    }



class qsireconInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class qsireconOutputSpec(TraitedSpec):
    output_dir = traits.String(desc="qsirecon output directory")
    
class qsirecon_pan(BaseInterface):
    input_spec = qsireconInputSpec
    output_spec = qsireconOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = qsirecon_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="qsirecon_node",input_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(qsirecon_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}") 
           
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None or input_dir == "":
        input_dir = substitute_labels("<QSIPREP_OUTPUT_DIR>", labels_dict)
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


