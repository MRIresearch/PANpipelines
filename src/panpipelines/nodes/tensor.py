from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob

def tensor_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    output_dir = cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    input_dir=substitute_labels(input_dir,labels_dict)
    dwi = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-*','dwi','*_desc-preproc_dwi.nii.gz'))
    bval = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-*','dwi','*_desc-preproc_dwi.bval'))
    bvec = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-*','dwi','*_desc-preproc_dwi.bvec'))
    mask = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-*','dwi','*_desc-brain_mask.nii.gz'))

    session_label=get_bidstag("ses",os.path.basename(dwi))

    tensor_dir = os.path.join(cwd,'tensors')
    if not os.path.isdir(tensor_dir):
        os.makedirs(tensor_dir)
    tensor_mrtrix = os.path.join(tensor_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_tensor.mif'.format(session_label),labels_dict))
    kurtosis_mrtrix = os.path.join(tensor_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_kurtosis.mif'.format(session_label),labels_dict))
   


    # generate tensors using mrtrix
    params="-fslgrad "+bvec+" "+bval+\
        " -mask "+mask+\
        " -dkt "+kurtosis_mrtrix+\
        " "+dwi+\
        " "+tensor_mrtrix

    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> dwi2tensor"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    
    # generate tensor metrics
    tensor_metrics_dir = os.path.join(cwd,'tensor_metrics')
    if not os.path.isdir(tensor_metrics_dir):
        os.makedirs(tensor_metrics_dir)

    fa_mrtrix = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-fa.mif'.format(session_label), labels_dict))
    adc_mrtrix = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-adc.mif'.format(session_label), labels_dict))
    ad_mrtrix = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-ad.mif'.format(session_label), labels_dict))
    rd_mrtrix = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-rd.mif'.format(session_label), labels_dict))

    # generate tensors using mrtrix
    params=" -mask "+mask+\
        " -fa "+fa_mrtrix+\
        " -adc "+adc_mrtrix+\
        " -ad "+ad_mrtrix+\
        " -rd "+rd_mrtrix+\
        " "+tensor_mrtrix

    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> tensor2metric"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)


    # convert to nifti
    fa_fsl = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-fa.nii.gz'.format(session_label), labels_dict))
    adc_fsl = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-adc.nii.gz'.format(session_label), labels_dict))
    ad_fsl = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-ad.nii.gz'.format(session_label), labels_dict))
    rd_fsl = os.path.join(tensor_metrics_dir,substitute_labels('sub-<PARTICIPANT_LABEL>_{}_space-T1w_desc-preproc_desc-rd.nii.gz'.format(session_label), labels_dict)) 

    # generate tensors using mrtrix
    params=fa_mrtrix+" "+ fa_fsl
    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    params=adc_mrtrix+" "+ adc_fsl
    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    params=ad_mrtrix+" "+ ad_fsl
    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    params=rd_mrtrix+" "+ rd_fsl
    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    out_files=[]
    out_files.insert(0,fa_fsl)
    out_files.insert(1,adc_fsl)
    out_files.insert(2,ad_fsl)
    out_files.insert(3,rd_fsl)


    return {
        "fa":fa_fsl,
        "adc":adc_fsl,
        "ad":ad_fsl,
        "rd":rd_fsl,
        "output_dir":output_dir,
        "out_files":out_files
    }



class tensorInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="QSIPREP Output Directory", usedefault=True)

class tensorOutputSpec(TraitedSpec):
    fa = File(desc='FA')
    adc = File(desc='ADC')
    ad = File(desc='AD')
    rd = File(desc='RD')
    output_dir = traits.String(desc="NODDI output directory")
    out_files = traits.List(desc='list of files')
    
class tensor_pan(BaseInterface):
    input_spec = tensorInputSpec
    output_spec = tensorOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = tensor_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="tensor_node",input_dir=""):
    # Create Node
    pan_node = Node(tensor_pan(), name=name)
    # Specify node inputs

    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None:
        input_dir = ""
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


