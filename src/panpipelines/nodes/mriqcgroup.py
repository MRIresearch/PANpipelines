from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from shutil import copytree
from nipype import logging as nlogging
from bids import BIDSLayout

IFLOGGER=nlogging.getLogger('nipype.interface')

IS_PRESENT="^^^"
IGNORE="###"

def mriqcgroup_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    mriqcgroup_outdir=os.path.join(cwd,"mriqcgroupout")
    os.makedirs(mriqcgroup_outdir,exist_ok=True)

    command_base, container = getContainer(labels_dict,nodename="mriqc", SPECIFIC="MRIQC_CONTAINER",LOGGER=IFLOGGER)
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)

    IFLOGGER.info("Checking the mriqc version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    
    participants_label = getParams(labels_dict,'GROUP_PARTICIPANTS_LABEL')
    participants_project = getParams(labels_dict,'GROUP_PARTICIPANTS_XNAT_PROJECT')
    participants_session = getParams(labels_dict,'GROUP_SESSION_LABEL')
    subject_list =[]
    if participants_label:
        for part_vals in zip(participants_project,participants_label,participants_session):
            project= part_vals[0]
            subject=part_vals[1]
            session = part_vals[2]
            subject_list.append(f"{project}^{subject}^{session}")

    mriqc_sourcedir_template = getParams(labels_dict,"MRIQC_OUTPUT_DIR")

    try:
        # Link mriqc subject folder
        for part_value in subject_list:
            part_vals = part_value.split("^")
            project = part_vals[0]
            subject = part_vals[1]
            session = part_vals[2]
            labels_dict = updateParams(labels_dict,"PARTICIPANT_LABEL",subject)
            labels_dict = updateParams(labels_dict,"PARTICIPANT_XNAT_PROJECT",project)
            labels_dict = updateParams(labels_dict,"PARTICIPANT_SESSION",session)
            mriqc_sourcedir_sub = os.path.join(substitute_labels(mriqc_sourcedir_template,labels_dict),f"sub-{subject}")
            mriqc_targetdir_sub = os.path.join(mriqcgroup_outdir,f"sub-{subject}")
            # create symlink at subject level, this should create for first session as we sorted list
            if not os.path.exists(mriqc_targetdir_sub) and os.path.exists(mriqc_sourcedir_sub):
                os.symlink(mriqc_sourcedir_sub,mriqc_targetdir_sub)

            # A few cases have multiple sessions, we physically copy these the first time. this code will only really be run once
            # for each subject as subsequent runs will have the session physically in the original mriqc directory.
            # This is probably not an ideal approach but it keeps the individual mriqc runs for each session independent.
            mriqc_sourcedir_ses = os.path.join(substitute_labels(mriqc_sourcedir_template,labels_dict),f"sub-{subject}",f"ses-{session}")
            mriqc_targetdir_ses = os.path.join(mriqcgroup_outdir,f"sub-{subject}",f"ses-{session}")
            if not os.path.exists(mriqc_targetdir_ses) and os.path.exists(mriqc_sourcedir_ses):
                copytree(mriqc_sourcedir_ses,mriqc_targetdir_ses)
            
            
        # handle field maps - use dwirpe as standard if valid, otherwise use megre
        if not bids_dir:
            bids_dir = substitute_labels('<BIDS_DIR>', labels_dict)

        mriqc_dict={}
        mriqc_dict = updateParams(mriqc_dict,"-w","<CWD>/mriqcgroupwork")

        # Additional params
        MRIQC_OVERRIDE_PARAMS = getParams(labels_dict,"MRIQC_OVERRIDE_PARAMS")
        if MRIQC_OVERRIDE_PARAMS and isinstance(MRIQC_OVERRIDE_PARAMS,dict):
            add_labels(MRIQC_OVERRIDE_PARAMS,mriqc_dict)
    

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
                " "+ mriqcgroup_outdir +\
                " group"\
                " "+ params 

        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

        bold_rep = getGlob(os.path.join(cwd,'mriqcgroupout','*bold.tsv'))
        t1w_rep = getGlob(os.path.join(cwd,'mriqcgroupout','*T1w.tsv'))
        t2w_rep= getGlob(os.path.join(cwd,'mriqcgroupout','*T2w.tsv'))
        dwi_rep = getGlob(os.path.join(cwd,'mriqcgroupout','*dwi.tsv'))

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
            "output_dir":mriqcgroup_outdir,
            "out_files":out_files
        }
    except Exception as e:
        IFLOGGER.error(f"Exception created {e} - will try to unlink all mriqc subfolders at {mriqcgroup_outdir}")
        raise(e)
    finally:
        IFLOGGER.info(f"Attempting to unlink all subfolders at {mriqcgroup_outdir}")
        for part_value in subject_list:
            part_vals = part_value.split("^")
            subject = part_vals[1]
            mriqc_targetdir_sub = os.path.join(mriqcgroup_outdir,f"sub-{subject}")
            if os.path.islink(mriqc_targetdir_sub):
                os.unlink(mriqc_targetdir_sub)
        


class mriqcgroupInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class mriqcgroupOutputSpec(TraitedSpec):
    output_dir = traits.Directory(desc="MRIQC group output directory")
    out_files = traits.List(desc='list of files')
    
class mriqcgroup_pan(BaseInterface):
    input_spec = mriqcgroupInputSpec
    output_spec = mriqcgroupOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = mriqcgroup_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='mriqcgroup_node',bids_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(mriqcgroup_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


