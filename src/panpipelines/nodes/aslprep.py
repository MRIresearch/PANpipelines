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
 
def aslprep_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    if not bids_dir:
        bids_dir = substitute_labels(labels_dict,"<BIDS_DIR>")

    command_base, container = getContainer(labels_dict,nodename="aslprep",SPECIFIC="ASLPREP_CONTAINER",LOGGER=IFLOGGER)
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)

    IFLOGGER.info("Checking the aslprep version:")
    command = f"{command_base} --version"
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')
    participant_project = getParams(labels_dict,"PARTICIPANT_XNAT_PROJECT")

    UM_EXCEPTION = False
    if participant_project == "002_HML":
        part_df = pd.read_csv(os.path.join(bids_dir,"participants.tsv"),sep="\t")
        search_df = part_df[(part_df["participant_id"]=="sub-" + drop_sub(participant_label)) & (part_df["session_id"] == "ses-" + drop_ses(participant_session))]
        if not search_df.empty:
            scantime = search_df.iloc[0]["mri_scan_datetime"]
            if datetime.datetime.strptime(scantime,"%Y-%m-%dT%H:%M:%S.%f%Z") > datetime.datetime(2024,10,21):
                UM_EXCEPTION = True

    
    if UM_EXCEPTION:
        IFLOGGER.info("Conversion to XA50 software at 002_HML added 1 extra volume to M0 and ASL scans. These have been removed from their BIDS files.")
        #new_bids_dir = os.path.join(cwd,"bids_dir")
        #copytree(os.path.join(bids_dir,f"sub-{participant_label}"),os.path.join(new_bids_dir,f"sub-{participant_label}"))
        #copy(os.path.join(bids_dir,"participants.tsv"),os.path.join(new_bids_dir,"participants.tsv"))
        #copy(os.path.join(bids_dir,"dataset_description.json"),os.path.join(new_bids_dir,"dataset_description.json"))
        #bids_dir = new_bids_dir
        #process_um_exception(bids_dir, cwd, participant_label, participant_session,labels_dict)

    aslprep_dict={}
    aslprep_dict = updateParams(aslprep_dict,"--participant_label","<PARTICIPANT_LABEL>")
    aslprep_dict = updateParams(aslprep_dict,"--low-mem",IS_PRESENT)
    aslprep_dict = updateParams(aslprep_dict,"--skip-bids-validation",IS_PRESENT)
    aslprep_dict = updateParams(aslprep_dict,"--stop-on-first-crash",IS_PRESENT)
    aslprep_dict = updateParams(aslprep_dict,"--mem_mb","<BIDSAPP_MEMORY>")
    aslprep_dict = updateParams(aslprep_dict,"--nthreads","<BIDSAPP_THREADS>")
    aslprep_dict = updateParams(aslprep_dict,"--fs-license-file","<FSLICENSE>")
    aslprep_dict = updateParams(aslprep_dict,"-w","<CWD>/aslprep_work")

    # Additional params
    ASLPREP_OVERRIDE_PARAMS = getParams(labels_dict,"ASLPREP_OVERRIDE_PARAMS")
    if ASLPREP_OVERRIDE_PARAMS and isinstance(ASLPREP_OVERRIDE_PARAMS,dict):
        add_labels(ASLPREP_OVERRIDE_PARAMS,aslprep_dict)        

    params = ""
    for aslprep_tag, aslprep_value in aslprep_dict.items():
        if "--" in aslprep_tag and "---" not in aslprep_tag:
            if aslprep_value == IS_PRESENT:
                params=params + " " + aslprep_tag
            elif aslprep_value == IGNORE:
                IFLOGGER.info(f"Parameter {aslprep_tag} is being skipped. This has been explicitly required in configuration.")
            else:
                # we dont need = sign for fmriprep just for basi;
                params = params + " " + aslprep_tag + " " + aslprep_value

        elif "-" in aslprep_tag and "--" not in aslprep_tag:
            params = params + " " + aslprep_tag + " " + aslprep_value

        else:
            print(f"aslprep tag {aslprep_tag} not valid.") 

    command = f"{command_base}"\
        f" {bids_dir}"\
        " <CWD>"\
        " participant"\
        " " + params
        
    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    cbf_preprocess = getGlob(os.path.join(cwd,'aslprep','sub-{}'.format(participant_label),'ses-*','perf','*cbf.nii.gz'))
    mat_t12perf = getGlob(os.path.join(cwd,'aslprep','sub-{}'.format(participant_label),'ses-*','perf','*from-T1w*mode-image_xfm.txt'))
    mat_perf2t1 = getGlob(os.path.join(cwd,'aslprep','sub-{}'.format(participant_label),'ses-*','perf','*from-scanner*mode-image_xfm.txt'))
    mat_t12mni = getGlob(os.path.join(cwd,'aslprep','sub-{}'.format(participant_label),'ses-*','anat','*from-T1w*mode-image_xfm.h5'))
    mat_mni2t1 = getGlob(os.path.join(cwd,'aslprep','sub-{}'.format(participant_label),'ses-*','anat','*from-MNI*mode-image_xfm.h5'))
    anatrefs =  glob.glob(os.path.join(cwd,'aslprep','sub-{}'.format(participant_label),'ses-*','anat','*{}*_desc-preproc_T1w.nii.gz'.format(participant_label)))
    t1ref = getFirstFromList([ s for s in anatrefs if "MNI" not in s])
    mniref = getFirstFromList([ s for s in anatrefs if "MNI" in s])
    output_dir = cwd

    
    out_files=[]
    out_files.insert(0,cbf_preprocess)
    out_files.insert(1,mat_t12perf)
    out_files.insert(2,mat_perf2t1)
    out_files.insert(3,mat_t12mni)
    out_files.insert(4,mat_mni2t1)
    out_files.insert(5,mniref)
    out_files.insert(6,t1ref)


    return {
        "cbf_preprocess":cbf_preprocess,
        "mat_t12perf":mat_t12perf,
        "mat_perf2t1":mat_perf2t1,
        "mat_t12mni":mat_t12mni,
        "mat_mni2t1":mat_mni2t1,
        "mniref":mniref,
        "t1ref":t1ref,
        "output_dir":output_dir,
        "out_files":out_files
    }



class aslprepInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class aslprepOutputSpec(TraitedSpec):
    cbf_preprocess = File(desc='Preprocessed CBF')
    mat_t12perf = File(desc='T1 to CBF/perfusion transform')
    mat_perf2t1 = File(desc='CBF/perfusion to T1 transform')
    mat_t12mni = File(desc='T1 to MNI transform')
    mat_mni2t1 = File(desc='MNI to T1 transform')
    mniref = File(desc='MNI reference')
    t1ref = File(desc='T1 reference')
    output_dir = traits.String(desc="ASLPREP output directory")
    out_files = traits.List(desc='list of files')
    
class aslprep_pan(BaseInterface):
    input_spec = aslprepInputSpec
    output_spec = aslprepOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = aslprep_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='aslprep_node',bids_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(aslprep_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


