from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def tensor_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    output_dir = cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    if not session_label:
        search_session_label="*"
    else:
        search_session_label=session_label

    input_dir=substitute_labels(input_dir,labels_dict)
    dwi = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-preproc_dwi.nii.gz'))
    bval = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-preproc_dwi.bval'))
    bvec = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-preproc_dwi.bvec'))
    mask = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-brain_mask.nii.gz'))

    tensor_dir = os.path.join(cwd,'tensors')
    if not os.path.isdir(tensor_dir):
        os.makedirs(tensor_dir)

    if not session_label:
        session_label=get_bidstag("ses",os.path.basename(dwi))
        if not session_label:
            tensor_mrtrix = os.path.join(tensor_dir,'sub-{}_tensor.mif'.format(participant_label))
            kurtosis_mrtrix = os.path.join(tensor_dir,'sub-{}_kurtosis.mif'.format(participant_label))
        else:
            tensor_mrtrix = os.path.join(tensor_dir,'sub-{}_ses-{}_tensor.mif'.format(participant_label,session_label))
            kurtosis_mrtrix = os.path.join(tensor_dir,'sub-{}_ses-{}_kurtosis.mif'.format(participant_label,session_label))           
    else:
        tensor_mrtrix = os.path.join(tensor_dir,'sub-{}_ses-{}_tensor.mif'.format(participant_label,session_label))
        kurtosis_mrtrix = os.path.join(tensor_dir,'sub-{}_ses-{}_kurtosis.mif'.format(participant_label,session_label))

    container_run_options = getParams(labels_dict,'CONTAINER_RUN_OPTIONS')
    if not container_run_options:
        container_run_options = ""

    container_prerun = getParams(labels_dict,'CONTAINER_PRERUN')
    if not container_prerun:
        container_prerun = ""

    container = getParams(labels_dict,'CONTAINER')
    if not container:
        container = getParams(labels_dict,'MRTRIX_CONTAINER')
        if not container:
            container = getParams(labels_dict,'NEURO_CONTAINER')
            if not container:
                IFLOGGER.info("Container not defined for Mrtrix pipeline. dwi2tensor, tensor2metric and mrconvert should be accessible on local path for pipeline to succeed")
                if container_run_options:
                    IFLOGGER.info("Note that '{container_run_options}' set as run options for non-existing container. This may cause the pipeline to fail.")
                
                if container_prerun:
                    IFLOGGER.info("Note that '{container_prerun}' set as pre-run options for non-existing container. This may cause the pipeline to fail.")

    command_base = f"{container_run_options} {container} {container_prerun}"
    if container:
        IFLOGGER.info("Checking the dwi2tensor version:")
        command = f"{command_base} dwi2tensor --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

        IFLOGGER.info("\nChecking the container version:")
        command = f"{command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    # generate tensors using mrtrix
    params="-fslgrad "+bvec+" "+bval+\
        " -mask "+mask+\
        " -dkt "+kurtosis_mrtrix+\
        " "+dwi+\
        " "+tensor_mrtrix

    command=f"{command_base} dwi2tensor"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)
    
    # generate tensor metrics
    tensor_metrics_dir = os.path.join(cwd,'tensor_metrics')
    if not os.path.isdir(tensor_metrics_dir):
        os.makedirs(tensor_metrics_dir)

    if not session_label:
        session_label=get_bidstag("ses",os.path.basename(dwi))
        if not session_label:
            fa_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-fa.mif'.format(participant_label))
            adc_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-adc.mif'.format(participant_label))
            ad_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-ad.mif'.format(participant_label))
            rd_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-rd.mif'.format(participant_label))   
        else:
            fa_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-fa.mif'.format(participant_label,session_label))
            adc_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-adc.mif'.format(participant_label,session_label))
            ad_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-ad.mif'.format(participant_label,session_label))
            rd_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-rd.mif'.format(participant_label,session_label))      
    else:
        fa_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-fa.mif'.format(participant_label,session_label))
        adc_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-adc.mif'.format(participant_label,session_label))
        ad_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-ad.mif'.format(participant_label,session_label))
        rd_mrtrix = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-rd.mif'.format(participant_label,session_label))


    # generate tensors using mrtrix
    params=" -mask "+mask+\
        " -fa "+fa_mrtrix+\
        " -adc "+adc_mrtrix+\
        " -ad "+ad_mrtrix+\
        " -rd "+rd_mrtrix+\
        " "+tensor_mrtrix

    command=f"{command_base} tensor2metric"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

    # convert to nifti
    if not session_label:
        session_label=get_bidstag("ses",os.path.basename(dwi))
        if not session_label:
            fa_fsl = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-fa.nii.gz'.format(participant_label))
            adc_fsl = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-adc.nii.gz'.format(participant_label))
            ad_fsl = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-ad.nii.gz'.format(participant_label))
            rd_fsl = os.path.join(tensor_metrics_dir,'sub-{}_space-T1w_desc-preproc_desc-rd.nii.gz'.format(participant_label))  
        else:
            fa_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-fa.nii.gz'.format(participant_label,session_label))
            adc_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-adc.nii.gz'.format(participant_label,session_label))
            ad_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-ad.nii.gz'.format(participant_label,session_label))
            rd_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-rd.nii.gz'.format(participant_label,session_label))     
    else:
        fa_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-fa.nii.gz'.format(participant_label,session_label))
        adc_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-adc.nii.gz'.format(participant_label,session_label))
        ad_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-ad.nii.gz'.format(participant_label,session_label))
        rd_fsl = os.path.join(tensor_metrics_dir,'sub-{}_ses-{}_space-T1w_desc-preproc_desc-rd.nii.gz'.format(participant_label,session_label)) 


    # generate tensors using mrtrix
    params=fa_mrtrix+" "+ fa_fsl
    command=f"{command_base} mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

    params=adc_mrtrix+" "+ adc_fsl
    command=f"{command_base} mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

    params=ad_mrtrix+" "+ ad_fsl
    command=f"{command_base} mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

    params=rd_mrtrix+" "+ rd_fsl
    command=f"{command_base} mrconvert"\
            " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    IFLOGGER.info(evaluated_command)
    evaluated_command_args = shlex.split(evaluated_command)
    results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
    IFLOGGER.info(results.stdout)

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


def create(labels_dict,name="tensor_node",input_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(tensor_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None:
        input_dir = ""
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


