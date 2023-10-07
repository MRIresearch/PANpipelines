from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob

def noddi_proc(labels_dict,input_dir):

    input_dir=substitute_labels(input_dir,labels_dict)

    params="--participant_label <PARTICIPANT_LABEL>" \
        " --recon_input "+input_dir+\
        " --recon_spec <RECON_TYPE>"\
        " --recon-only"\
        " --mem_mb <BIDSAPP_MEMORY>"\
        " --nthreads <BIDSAPP_THREADS>"\
        " --fs-license-file <FSLICENSE>"\
        " --skip-bids-validation"\
        " --skip-odf-report"\
        " -w <CWD>/noddi_work"\
        " --output-resolution <OUTPUT_RES>" 


    command="singularity run --cleanenv --no-home <QSIPREP_CONTAINER>"\
            " <BIDS_DIR>"\
            " <CWD>"\
            " participant"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    cwd=os.getcwd()
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    icvf = getGlob(os.path.join(cwd,'qsirecon','sub-{}'.format(participant_label),'ses-*','dwi','*ICVF_NODDI.nii.gz'))
    isovf = getGlob(os.path.join(cwd,'qsirecon','sub-{}'.format(participant_label),'ses-*','dwi','*ISOVF_NODDI.nii.gz'))
    od = getGlob(os.path.join(cwd,'qsirecon','sub-{}'.format(participant_label),'ses-*','dwi','*OD_NODDI.nii.gz'))
    directions =  getGlob(os.path.join(cwd,'qsirecon','sub-{}'.format(participant_label),'ses-*','dwi','*directions_NODDI.nii.gz'))
    output_dir = cwd

    
    out_files=[]
    out_files.insert(0,icvf)
    out_files.insert(1,isovf)
    out_files.insert(2,od)
    out_files.insert(3,directions)


    return {
        "icvf":icvf,
        "isovf":isovf,
        "od":od,
        "directions":directions,
        "output_dir":output_dir,
        "out_files":out_files
    }



class noddiInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class noddiOutputSpec(TraitedSpec):
    icvf = File(desc='ICVF')
    isovf = File(desc='ISOVF')
    od = File(desc='OD')
    directions = File(desc='Directions')
    output_dir = traits.String(desc="NODDI output directory")
    out_files = traits.List(desc='list of files')
    
class noddi_pan(BaseInterface):
    input_spec = noddiInputSpec
    output_spec = noddiOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = noddi_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="noddi_node",input_dir=""):
    # Create Node
    pan_node = Node(noddi_pan(), name=name)
    # Specify node inputs

    labels_dict = updateParams(labels_dict,"RECON_TYPE","amico_noddi")
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None or input_dir == "":
        input_dir = substitute_labels("<QSIPREP_OUTPUT>", labels_dict)
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


