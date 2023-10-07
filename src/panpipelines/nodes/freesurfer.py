from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
from bids import BIDSLayout

def freesurfer_proc(labels_dict,bids_dir=""):

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    layout = BIDSLayout(bids_dir)
    T1w=layout.get(subject=participant_label,suffix='T1w', extension='nii.gz')
    if T1w:
        T1wfile=T1w[0].path

    T2wLabel = getParams(labels_dict,'T2W_LABEL')
    t2w_entity=get_entities(T2wLabel)
    t2w_entity["subject"]=participant_label
    t2w_entity["extension"]='nii.gz'
    t2w_entity["suffix"]='T2w'
    T2w = layout.get(return_type='file', invalid_filters='allow', **t2w_entity)

    if T2w:
        T2wfile=T2w[0]

    HippoLabel = getParams(labels_dict,'HIPPO_LABEL')

    subject="sub-"+participant_label
    cwd=os.getcwd()
    subjects_dir = os.path.join(cwd,'subjects_dir')
    if not os.path.isdir(subjects_dir):
        os.makedirs(subjects_dir)

    if not os.path.exists(os.path.join(subjects_dir,"sub-"+participant_label,"recon-all.log")):
        params="-all" \
            " -i " + T1wfile + \
            " -subject " + subject + \
            " -parallel" \
            " -openmp <BIDSAPP_THREADS>"

        command="singularity run --cleanenv --nv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+subjects_dir+" recon-all"\
                " "+params
    else:
        params="-all" \
            " -no-isrunning" \
            " -subject " + subject + \
            " -parallel" \
            " -openmp <BIDSAPP_THREADS>"

        command="singularity run --cleanenv --nv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+subjects_dir+" recon-all"\
                " "+params


    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)


    # Hipposubfields segmentation using T2 and T1
    useT1="1"
    params= subject + \
        " " + T2wfile + \
        " " + HippoLabel + \
        " " + useT1

    command="singularity run --cleanenv --nv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+subjects_dir+" segmentHA_T2.sh"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)


    # Thalamic Segmentation 
    params= subject

    command="singularity run --cleanenv --nv --no-home <NEURO_CONTAINER> <FREEBASH_SCRIPT> "+subjects_dir+" segmentThalamicNuclei.sh"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)
 
    L_hipposubfields = getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','hipposubfields.lh.*{}*'.format(HippoLabel)))   
    R_hipposubfields = getGlob(os.path.join(subjects_dir,'sub-{}'.format(participant_label),'stats','hipposubfields.rh.*{}*'.format(HippoLabel)))
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


def create(labels_dict,name='freesurfer_node',bids_dir=""):
    # Create Node
    pan_node = Node(freesurfer_pan(), name=name)
    # Specify node inputs

    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


