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

def fslanat_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    command_base, container = getContainer(labels_dict,nodename="fslanat", SPECIFIC="FSL_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the fsl version:")
    command = f"{command_base} fslversion"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session= getParams(labels_dict,'PARTICIPANT_SESSION')
    layout = BIDSLayout(bids_dir)
    T1w=layout.get(subject=participant_label,session=participant_session,suffix='T1w', extension='nii.gz')
    if T1w:
        structin=T1w[0].path
        structout=os.path.join(cwd,"{}_struct".format(participant_label))

    params = "--nocrop "\
             " -i " + structin + \
             " -o " + structout

    command=f"{command_base} fsl_anat"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    fslanat_dir = structout + ".anat"
    T1w_biascorr = getGlob(os.path.join(fslanat_dir,"T1_biascorr.nii.gz"))
    T1w_biascorr_brain = getGlob(os.path.join(fslanat_dir,"T1_biascorr_brain.nii.gz"))
    T1w_biascorr_brain_mask = getGlob(os.path.join(fslanat_dir,"T1_biascorr_brain_mask.nii.gz"))
    out_files=[]
    out_files.insert(0,T1w_biascorr)
    out_files.insert(1,T1w_biascorr_brain)
    out_files.insert(2,T1w_biascorr_brain_mask)


    return {
        "T1w_biascorr":T1w_biascorr,
        "T1w_biascorr_brain":T1w_biascorr_brain,
        "T1w_biascorr_brain_mask":T1w_biascorr_brain_mask,
        "fslanat_dir":fslanat_dir,
        "out_files":out_files
    }


class fslanatInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class fslanatOutputSpec(TraitedSpec):
    T1w_biascorr = File(desc='T1w_biascorr')
    T1w_biascorr_brain = File(desc='T1w_biascorr_brain')
    T1w_biascorr_brain_mask = File(desc='T1w_biascorr_brain_mask')
    fslanat_dir = traits.String(desc="output directory of fsl_anat output")
    out_files = traits.List(desc='list of files')
    
class fslanat_pan(BaseInterface):
    input_spec = fslanatInputSpec
    output_spec = fslanatOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = fslanat_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="fslanat_node",bids_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(fslanat_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


