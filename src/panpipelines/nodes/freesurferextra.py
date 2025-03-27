from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
from bids import BIDSLayout
import shlex
import subprocess
from nipype import logging as nlogging
import datetime

IFLOGGER=nlogging.getLogger('nipype.interface')

def freesurferextra_proc(labels_dict,subjects_dir=""):

    command_base, container = getContainer(labels_dict,nodename="freesurferextra", SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER) 
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')

    subject="sub-"+participant_label
    session="ses-"+session_label

    resultsmessage=[]
    resultsmessage.append(f"Started freesurfer extra processing for {subject},{session}\n")
    resultsmessage.append(f"Datetime started: {str(datetime.datetime.now())}\n")

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    if not subjects_dir:
        subjects_dir = getParams(labels_dict,'SUBJECTS_DIR')

    os.environ["SUBJECTS_DIR"]=subjects_dir
    os.environ["SINGULARITYENV_SUBJECTS_DIR"]=translate_binding(command_base,subjects_dir)
  
    FREEVER="Unknown"
    IFLOGGER.info("Checking the recon-all version:")
    command = f"{command_base} recon-all --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    if "-7.3.2-" in results:
        FREEVER="7.3.2"
    resultsmessage.append(results)

    IFLOGGER.info("\nChecking the container version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    resultsmessage.append(results)

    # create lobe lh
    command=f"{command_base} mri_annotation2label --subject {subject} --hemi lh  --lobesStrict lh.lobes.annot"
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    resultsmessage.append(results)

    # create lobe rh
    command=f"{command_base} mri_annotation2label --subject {subject} --hemi rh  --lobesStrict rh.lobes.annot"
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    resultsmessage.append(results)

    lobestats_lh=os.path.join(subjects_dir,subject, "stats","lh.lobe.stats")
    command=f"{command_base} mris_anatomical_stats -a lobes.annot -f {lobestats_lh} {subject} lh"
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    resultsmessage.append(results)

    lobestats_rh=os.path.join(subjects_dir,subject, "stats","rh.lobe.stats")
    command=f"{command_base} mris_anatomical_stats -a lobes.annot -f {lobestats_rh} {subject} rh"
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    resultsmessage.append(results)

    resultsmessage.append(f"Completed freesurfer extra processing for {subject},{session}\n")
    resultsmessage.append(f"\nDatetime Completed: {str(datetime.datetime.now())}\n")

    resultsfile=os.path.join(cwd,f"{subject}_{session}_completed")
    with open(resultsfile,"w") as outfile:
        outfile.write("\n".join(resultsmessage))
    
    out_files=[]
    out_files.insert(0,lobestats_lh)
    out_files.insert(1,lobestats_rh)


    return {
        "output_dir":output_dir,
        "out_files":out_files
    }



class freesurferextraInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    subjects_dir = traits.String("",desc="Freesurfer Directory", usedefault=True)

class freesurferextraOutputSpec(TraitedSpec):
    output_dir = traits.String(desc="freesurferextra output directory")
    out_files = traits.List(desc='list of files')
    
class freesurferextra_pan(BaseInterface):
    input_spec = freesurferextraInputSpec
    output_spec = freesurferextraOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = freesurferextra_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='freesurferextra_node',subjects_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(freesurferextra_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if subjects_dir is None or subjects_dir == "":
        subjects_dir = substitute_labels("<SUBJECTS_DIR>", labels_dict)

    pan_node.inputs.subjects_dir =  subjects_dir

    return pan_node


