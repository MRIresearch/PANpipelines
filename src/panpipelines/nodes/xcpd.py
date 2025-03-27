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

def xcpd_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    command_base, container = getContainer(labels_dict,nodename="xcpd", SPECIFIC="XCPD_CONTAINER",LOGGER=IFLOGGER)

    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["APPTAINERENV_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)
    
    IFLOGGER.info("Checking the xcpd version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    input_dir =substitute_labels(input_dir,labels_dict)
    output_dir =substitute_labels("<CWD>/xcp_out", labels_dict)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    work_dir = substitute_labels("<CWD>/xcpd_work", labels_dict)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir,exist_ok=True)

    # set up dwi to process just the specific dwi session
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    xcpd_dict={}
    xcpd_dict = updateParams(xcpd_dict,"--participant_label","<PARTICIPANT_LABEL>")
    xcpd_dict = updateParams(xcpd_dict,"--smoothing","0")
    xcpd_dict = updateParams(xcpd_dict,"--fd-thresh","0.5")
    xcpd_dict = updateParams(xcpd_dict,"--datasets","aal=/custom_atlases/aal yeobuckner=/custom_atlases/yeobuckner schaefer=/custom_atlases/schaefer")
    xcpd_dict = updateParams(xcpd_dict,"--atlases","AAL3 yeobuckner131 yeobuckner58 schaefer1000 schaefer1000b")
    
    xcpd_dict = updateParams(xcpd_dict,"--mem_gb","<BIDSAPP_MEMORY_GB>")
    xcpd_dict = updateParams(xcpd_dict,"--nthreads","<BIDSAPP_THREADS>")
    xcpd_dict = updateParams(xcpd_dict,"--omp_nthreads","1")
    xcpd_dict = updateParams(xcpd_dict,"--fs-license-file","<FSLICENSE>")
    xcpd_dict = updateParams(xcpd_dict,"-w",work_dir)

    xcpd_dict = updateParams(xcpd_dict,"--input-type", "fmriprep")
    xcpd_dict = updateParams(xcpd_dict,"--mode", "none")
    xcpd_dict = updateParams(xcpd_dict,"--abcc-qc", "n")
    xcpd_dict = updateParams(xcpd_dict,"--combine-runs", "n")
    xcpd_dict = updateParams(xcpd_dict,"--nuisance-regressors", "36P")
    xcpd_dict = updateParams(xcpd_dict,"--despike", "y")
    xcpd_dict = updateParams(xcpd_dict,"--file-format", "nifti")
    xcpd_dict = updateParams(xcpd_dict,"--linc-qc", "n")
    xcpd_dict = updateParams(xcpd_dict,"--min-coverage", "0")
    xcpd_dict = updateParams(xcpd_dict,"--motion-filter-type", "none")
    xcpd_dict = updateParams(xcpd_dict,"--output-type", "interpolated") 
    xcpd_dict = updateParams(xcpd_dict,"--warp-surfaces-native2std", "n") 
    xcpd_dict = updateParams(xcpd_dict,"--create-matrices", "all")

    # Additional params
    XCPD_OVERRIDE_PARAMS = getParams(labels_dict,"XCPD_OVERRIDE_PARAMS")
    if XCPD_OVERRIDE_PARAMS and isinstance(XCPD_OVERRIDE_PARAMS,dict):
        add_labels(XCPD_OVERRIDE_PARAMS,xcpd_dict)        

    params = ""
    for xcpd_tag, xcpd_value in xcpd_dict.items():
        if "--" in xcpd_tag and "---" not in xcpd_tag:
            if xcpd_value == IS_PRESENT:
                params=params + " " + xcpd_tag
            elif xcpd_value == IGNORE:
                IFLOGGER.info(f"Parameter {xcpd_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                # we dont need = sign for xcpd just for basi;
                params = params + " " + xcpd_tag + " " + xcpd_value

        elif "-" in xcpd_tag and "--" not in xcpd_tag:
            params = params + " " + xcpd_tag + " " + xcpd_value

        else:
            print(f"xcpd tag {xcpd_tag} not valid.") 

    command=f"{command_base}"\
            " " + input_dir +\
            " " + output_dir+\
            " participant"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    denoised_bold = getGlob(os.path.join(output_dir,'sub-{}'.format(participant_label),'ses-*','func','*desc-denoised_bold.nii.gz'))
    outliers = getGlob(os.path.join(output_dir,'sub-{}'.format(participant_label),'ses-*','func','*_outliers.tsv'))
    design = getGlob(os.path.join(output_dir,'sub-{}'.format(participant_label),'ses-*','func','*design.tsv'))
    motion_confounds = getGlob(os.path.join(output_dir,'sub-{}'.format(participant_label),'ses-*','func','*motion.tsv'))
    root_output_dir = cwd

    
    out_files=[]
    out_files.insert(0,denoised_bold)
    out_files.insert(1,outliers)
    out_files.insert(2,design)
    out_files.insert(3,motion_confounds)


    return {
        "denoised_bold": denoised_bold,
        "outliers": outliers,
        "design": design,
        "motion_confounds":motion_confounds,
        "output_dir":root_output_dir,
        "out_files":out_files
    }



class xcpdInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="FMRIPREP Directory", usedefault=True)

class xcpdOutputSpec(TraitedSpec):
    denoised_bold= File(desc='denoised_bold')
    outliers = File(desc='outliers')
    design = File(desc='design')
    motion_confounds= File(desc='motion_confounds')
    output_dir = traits.String(desc="XCPD output directory")
    out_files = traits.List(desc='list of files')
    
class xcpd_pan(BaseInterface):
    input_spec = xcpdInputSpec
    output_spec = xcpdOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = xcpd_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="xcpd_node",input_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(xcpd_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}") 
           
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None or input_dir == "":
        input_dir = substitute_labels("<FMRIPREP_OUTPUT_DIR>", labels_dict)
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


