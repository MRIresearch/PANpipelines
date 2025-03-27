from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def getbids_proc(labels_dict):
    cwd=os.getcwd()
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')
    getbids_file = os.path.join(cwd,f'sub-{participant_label}_ses-{participant_session}_log.txt')
    
    with open(getbids_file,"w") as outfile:
        outfile.write(f"sub-{participant_label}_ses-{participant_session} finished")
        
    out_files=[]
    out_files.append(getbids_file)

    return {
        "out_files" : out_files
    }

class getbidsInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)

class getbidsOutputSpec(TraitedSpec):
    out_files = traits.List(desc='list of files')
    
class getbids_pan(BaseInterface):
    input_spec = getbidsInputSpec
    output_spec = getbidsOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = getbids_proc(
            self.inputs.labels_dict,
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='getbids_node',LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(getbids_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
   
    return pan_node


