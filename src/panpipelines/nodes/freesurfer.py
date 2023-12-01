from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
from bids import BIDSLayout
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def freesurfer_proc(labels_dict,bids_dir=""):

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    layout = BIDSLayout(bids_dir)

    container_run_options = getParams(labels_dict,'CONTAINER_RUN_OPTIONS')
    if not container_run_options:
        container_run_options = ""

    container_prerun = getParams(labels_dict,'CONTAINER_PRERUN')
    if not container_prerun:
        container_prerun = ""

    container = getParams(labels_dict,'CONTAINER')
    if not container:
        container = getParams(labels_dict,'FREESURFER_CONTAINER')
        if not container:
            container = getParams(labels_dict,'NEURO_CONTAINER')
            if not container:
                IFLOGGER.info("Container not defined for Freesurfer pipeline. Recon-all should be accessible on local path for pipeline to succeed")
                if container_run_options:
                    IFLOGGER.info("Note that '{container_run_options}' set as run options for non-existing container. This may cause the pipeline to fail.")
                
                if container_prerun:
                    IFLOGGER.info("Note that '{container_prerun}' set as pre-run options for non-existing container. This may cause the pipeline to fail.")

    
    FREEVER="Unknown"
    command_base = f"{container_run_options} {container} {container_prerun}"
    if container:
        IFLOGGER.info("Checking the recon-all version:")
        command = f"{command_base} recon-all --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)
        if "-7.3.2-" in results.stdout:
            FREEVER="7.3.2"
        IFLOGGER.info("\nChecking the container version:")
        command = f"{command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    T1wfile=None
    T1wLabel = getParams(labels_dict,'T1W')
    t1w_entity={"acquisition": None, "reconstruction": None}
    if T1wLabel is not None:
        t1w_entity=add_labels(T1wLabel,t1w_entity)
        t1w_entity["subject"]=participant_label
        t1w_entity["extension"]='nii.gz'
        if session_label:
            t1w_entity["session"]=session_label
        T1w= layout.get(return_type='file', invalid_filters='allow', **t1w_entity)
        if T1w:
            T1wfile=T1w[0]
    else:
        T1w=layout.get(subject=participant_label,suffix='T1w', extension='nii.gz')
        if T1w:
            T1wfile=T1w[0].path

    HippoT2wfile=None
    HippoLabel = getParams(labels_dict,'HIPPO_T2W')
    hippo_t2w_entity={"acquisition": None, "reconstruction": None}
    if HippoLabel is not None:
        if "hippo_id" in HippoLabel.keys():
            hippo_id=HippoLabel["hippo_id"]
            HippoLabel.pop("hippo_id")
        else:
            hippo_id="T2w"
        hippo_t2w_entity=add_labels(HippoLabel,hippo_t2w_entity)
        hippo_t2w_entity["subject"]=participant_label
        hippo_t2w_entity["extension"]='nii.gz'
        if session_label:
            hippo_t2w_entity["session"]=session_label
        HippoT2w = layout.get(return_type='file', invalid_filters='allow', **hippo_t2w_entity)

        if HippoT2w:
            HippoT2wfile=HippoT2w[0]

    PialT2wfile=None
    PialLabel = getParams(labels_dict,'PIAL_T2W')
    pial_t2w_entity={"acquisition": None, "reconstruction": None}
    ISFLAIR=False
    if PialLabel is not None:
        pial_t2w_entity=add_labels(PialLabel,pial_t2w_entity)
        pial_t2w_entity["subject"]=participant_label
        pial_t2w_entity["extension"]='nii.gz'
        if session_label:
            pial_t2w_entity["session"]=session_label
        PialT2w = layout.get(invalid_filters='allow', **pial_t2w_entity)

        if PialT2w:
            PialT2wfile=PialT2w[0].path
            if PialT2w[0].entities['suffix'] == "FLAIR":
                ISFLAIR=True

    subject="sub-"+participant_label
    cwd=os.getcwd()
    subjects_dir = os.path.join(cwd,'subjects_dir')
    if not os.path.isdir(subjects_dir):
        os.makedirs(subjects_dir)

    os.environ["SINGULARITYENV_SUBJECTS_DIR"]=subjects_dir

    pial_t2_string = ""
    if PialT2wfile:
        if ISFLAIR:
            pial_t2_string = f" -FLAIR {PialT2wfile} -FLAIRpial"
            # https://github.com/freesurfer/freesurfer/issues/849
            # https://surfer.nmr.mgh.harvard.edu/fswiki/ReleaseNotes
            # Address issue with FLAIR-based pial reconstructions
            if FREEVER=="7.3.2":
                IFLOGGER.info("Due to known issue in Freesurfer 7.3.2 while using FLAIR images to reconstruct pial surface we will copy global-expert-options.txt to SUBJECTS_DIR")
                IFLOGGER.info("See https://github.com/freesurfer/freesurfer/issues/849 and https://surfer.nmr.mgh.harvard.edu/fswiki/ReleaseNotes")
                command=f"{command_base} cp /subjects_dir/global-expert-options.txt {subjects_dir}"
                evaluated_command=substitute_labels(command, labels_dict)
                IFLOGGER.info(evaluated_command)
                evaluated_command_args = shlex.split(evaluated_command)
                results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
                IFLOGGER.info(results.stdout)

        else:
            pial_t2_string = f" -T2 {PialT2wfile} -T2pial"

    if not os.path.exists(os.path.join(subjects_dir,"sub-"+participant_label,"recon-all.log")):
        params="-all" \
            " -i " + T1wfile + \
            " -subject " + subject + \
            " -parallel" \
            + pial_t2_string + \
            " -openmp <BIDSAPP_THREADS>"

        command=f"{command_base} recon-all"\
                " "+params
    else:
        params="-all" \
            " -no-isrunning" \
            " -subject " + subject + \
            " -parallel" \
            + pial_t2_string + \
            " -openmp <BIDSAPP_THREADS>"

        command=f"{command_base} recon-all"\
                " "+params


    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)


    # Hipposubfields segmentation just T1
    params= subject 

    command=f"{command_base} segmentHA_T1.sh"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

    # Test new beta Hipposubfields segmentation released in 7.3.2 that only uses T1
    params= " hippo-amygdala"\
            " --cross " + subject + \
            " --suffix beta" 

    command=f"{command_base} segment_subregions"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)


    if HippoT2wfile:
        # Hipposubfields segmentation using T2 and T1
        useT1="1"
        params= subject + \
            " " + HippoT2wfile + \
            " " + hippo_id + \
            " " + useT1

        command=f"{command_base} segmentHA_T2.sh"\
                " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

        # Hipposubfields segmentation using just T2
        useT1="0"
        params= subject + \
            " " + HippoT2wfile + \
            " " + hippo_id + \
            " " + useT1

        command=f"{command_base} segmentHA_T2.sh"\
                " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)
    else:
        hippo_id="T1"


    # Thalamic Segmentation 
    params= subject

    command=f"{command_base} segmentThalamicNuclei.sh"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

    # Test new beta Thalamic and Brainstem segmentation released in 7.3.2 that only uses T1
    params= " thalamus"\
            " --cross " + subject + \
            " --suffix beta_thalamus" 

    command=f"{command_base} segment_subregions"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)


    params= " brainstem"\
            " --cross " + subject + \
            " --suffix beta_brainstem" 

    command=f"{command_base} segment_subregions"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

 
    L_hipposubfields = getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','hipposubfields.lh.*{}*'.format(hippo_id)))   
    R_hipposubfields = getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','hipposubfields.rh.*{}*'.format(hippo_id)))
    L_a2009stats = getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','lh.aparc.a2009s.stats'))
    R_a2009stats = getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','rh.aparc.a2009s.stats'))
    asegstats =  getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','aseg.stats'))
    output_dir = cwd

    
    out_files=[]
    out_files.insert(0,L_hipposubfields)
    out_files.insert(1,R_hipposubfields)
    out_files.insert(2,L_a2009stats)
    out_files.insert(3,R_a2009stats)
    out_files.insert(4,asegstats)


    return {
        "L_hipposubfields": L_hipposubfields,
        "R_hipposubfields": R_hipposubfields,
        "L_a2009stats": L_a2009stats,
        "R_a2009stats": R_a2009stats,
        "asegstats": asegstats,
        "subjects_dir": subjects_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class freesurferInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class freesurferOutputSpec(TraitedSpec):
    L_hipposubfields = File(desc='Hipposubfield stats LH')
    R_hipposubfields = File(desc='Hipposubfield stats RH')
    L_a2009stats = File(desc='aparc stats LH')
    R_a2009stats = File(desc='aparc stats RH')
    asegstats = File(desc='aseg stats')
    subjects_dir = traits.String(desc="Freesurfer subjects directory")
    output_dir = traits.String(desc="Freesurfer output directory")
    out_files = traits.List(desc='list of files')
    
class freesurfer_pan(BaseInterface):
    input_spec = freesurferInputSpec
    output_spec = freesurferOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = freesurfer_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='freesurfer_node',bids_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(freesurfer_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


