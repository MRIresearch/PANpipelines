from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob

def aslprep_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    params = "--participant_label <PARTICIPANT_LABEL>" \
        " --low-mem"\
        " --skip-bids-validation"\
        " --stop-on-first-crash" \
        " --use-syn-sdc"\
        " --mem_mb <BIDSAPP_MEMORY>" \
        " --nthreads <BIDSAPP_THREADS>"\
        " --fs-license-file <FSLICENSE>"\
        " --ignore fieldmaps"\
        " -w <CWD>/aslprep_work"

    command = "singularity run --cleanenv --nv --no-home <ASLPREP_CONTAINER>"\
        " <BIDS_DIR>"\
        " <CWD>"\
        " participant"\
        " "+params


    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

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


def create(labels_dict,name='aslprep_node',bids_dir=""):
    # Create Node
    pan_node = Node(aslprep_pan(), name=name)
    # Specify node inputs

    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


