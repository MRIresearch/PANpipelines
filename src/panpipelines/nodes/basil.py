from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import nibabel as nb
from bids import BIDSLayout
import shlex
import subprocess
from nipype import logging as nlogging

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

IS_PRESENT="^^^"

def basil_proc(labels_dict,bids_dir="",fslanat_dir=""):

    container_run_options = getParams(labels_dict,'CONTAINER_RUN_OPTIONS')
    if not container_run_options:
        container_run_options = ""

    container_prerun = getParams(labels_dict,'CONTAINER_PRERUN')
    if not container_prerun:
        container_prerun = ""

    container = getParams(labels_dict,'CONTAINER')
    if not container:
        container = getParams(labels_dict,'BASIL_CONTAINER')
        if not container:
            container = getParams(labels_dict,'NEURO_CONTAINER')
            if not container:
                IFLOGGER.info("Container not defined for Freesurfer pipeline. oxford_asl should be accessible on local path for pipeline to succeed")
                if container_run_options:
                    IFLOGGER.info("Note that '{container_run_options}' set as run options for non-existing container. This may cause the pipeline to fail.")
                
                if container_prerun:
                    IFLOGGER.info("Note that '{container_prerun}' set as pre-run options for non-existing container. This may cause the pipeline to fail.")

    
    command_base = f"{container_run_options} {container} {container_prerun}"
    if container:
        IFLOGGER.info("Checking the oxford_asl version:")
        command = f"{command_base} oxford_asl --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

        IFLOGGER.info("\nChecking the container version:")
        command = f"{command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    basil_dict={}
    basil_dict = updateParams(basil_dict,MC,IS_PRESENT)
    basil_dict = updateParams(basil_dict,PVCORR,IS_PRESENT)
    basil_dict = updateParams(basil_dict,DEBUG,IS_PRESENT)
    basil_dict = updateParams(basil_dict,REGIONANALYSIS,IS_PRESENT)
    basil_dict = updateParams(basil_dict,FIXBAT,IS_PRESENT)
    
    cwd=os.getcwd()
    output_dir=os.path.join(cwd,"basiloutput")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    basil_dict = updateParams(basil_dict,ASL_OUTPUT,output_dir)

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    layout = BIDSLayout(bids_dir)

    fslanat_dir=os.path.abspath(fslanat_dir)
    basil_dict = updateParams(basil_dict,FSLANAT,fslanat_dir)

    asl=layout.get(subject=participant_label,suffix='asl', extension='nii.gz')

    if len(asl) > 0:
        asl_bidsfile=asl[0]
        asl_file=asl_bidsfile.path
        basil_dict = updateParams(basil_dict,ASL_INPUT,asl_file)
        asljson=asl_bidsfile.get_metadata()
        asl_entities = asl_bidsfile.get_entities()
        if "acquisition" in asl_entities.keys():
            asl_acq = "acq-" + asl_entities["acquisition"]
        else:
            asl_acq = get_bidstag("acq",asl_bidsfile.filename)

        asl_img = nb.load(asl_file)
        rpts=int(asl_img.header["dim"][4]/2)
        basil_dict = updateParams(basil_dict,IBF,'rpt')
        basil_dict = updateParams(basil_dict,RPTS,str(rpts))

        asl_type="PCASL"
        if "ArterialSpinLabelingType" in asljson.keys():
            asl_type = asljson["ArterialSpinLabelingType"]

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


        basil_dict = updateParams(basil_dict,IAF,"tc")
        ASLCONTEXT = getParams(labels_dict,"ASLCONTEXT")
        if ASLCONTEXT is not None and isinstance(ASLCONTEXT,dict):
            if asl_acq in ASLCONTEXT.keys():
                if ASLCONTEXT[asl_acq] == "control:label":
                    basil_dict = updateParams(basil_dict,IAF,"ct")
                elif ASLCONTEXT[asl_acq] == "label:control":
                    basil_dict = updateParams(basil_dict,IAF,"tc")

        CMETHOD_OPTS = getParams(labels_dict,"CMETHOD_OPTS")
        if CMETHOD_OPTS is not None and isinstance(CMETHOD_OPTS,dict):
            if asl_acq in CMETHOD_OPTS.keys():
                basil_dict = updateParams(basil_dict,CMETHOD,CMETHOD_OPTS[asl_acq])

        m0_entities = asl_entities.copy()
        m0_entities["suffix"]="m0scan"
        m0  = layout.get(return_type='file', invalid_filters='allow', **m0_entities)
        if len(m0) > 0:
            m0_file=m0[0]
            basil_dict = updateParams(basil_dict,CALIBRATION,m0_file)

        params = ""
        for basil_tag, basil_value in basil_dict.items():
            if "--" in basil_tag:
                if basil_value == IS_PRESENT:
                    params=params + " " + basil_tag
                else:
                    params = params + " " + basil_tag+"="+basil_value

            elif "-" in basil_tag and "--" not in basil_tag:
                params = params + " " + basil_tag + " " + basil_value

            else:
                print(f"Basil tag {basil_tag} not valid.")


        command=f"{command_base} oxford_asl"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)


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


