from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import os
import glob
import nibabel as nb
import pathlib
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def registration_proc(labels_dict,input_file,ref_file,registration_type):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir = cwd

    command_base, container = getContainer(labels_dict,nodename="registration",SPECIFIC="ANTS_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the ants version:")
    command = f"{command_base} antsRegistration --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    if container:
        IFLOGGER.info("\nChecking the container version:")
        command = f"{command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

    if Path(input_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir,exist_ok=True)

        fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
        input_file_nii = newfile(mgzdir,input_file,extension=".nii.gz")
        convMGZ2NII(input_file, input_file_nii, fs_command_base)
        input_file = input_file_nii

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    work_dir = os.path.join(cwd,f'{participant_label}_{participant_session}_workdir')
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir,exist_ok=True)

    transform_base = getParams(labels_dict,'TRANSFORM_NAME')
    transform = os.path.join(cwd,f"sub-{participant_label}_ses-{participant_session}_transform_{transform_base}")

    if registration_type == "ants_registration_rigid":
        transform_complete =ants_registration_rigid(input_file,ref_file,transform,command_base)
        out_file=transform_complete["out_file"]
    elif registration_type == "ants_registration_affine":
        transform_complete=ants_registration_affine(input_file,ref_file,transform,command_base)
        out_file=transform_complete["out_file"]
    elif registration_type == "ants_registration":
        transform_complete=ants_registration(input_file,ref_file,transform,command_base)
        out_file=transform_complete["out_file"]
    elif registration_type == "fsl_register_nonlin":
        transform_complete=fsl_register_nonlin(input_file,ref_file,transform,command_base)
        out_file=transform_complete["out_file"]
    elif registration_type == "fsl_reg_flirt_affine" or registration_type == "fsl_reg_flirt_rigid" :
        transform_complete={}
        out_file = newfile(assocfile=transform,suffix="desc-forward",extension="nii.gz")
        transform_forward = newfile(assocfile=transform,suffix="desc-forward",extension="mat")
        transform_complete["forward"]=transform_forward
        transform_complete["out_file"]= out_file
        if registration_type == "fsl_reg_flirt_affine":
            dof="12"
        else:
            dof="6"
        fsl_reg_flirt(input_file,ref_file,transout,transform_forward,command_base,dof=dof,cost="mutualinfo")
        transform_inverse = newfile(assocfile=transform,suffix="desc-inverse",extension="mat")
        transform_complete["inverse"]=transform_inverse
        invertAffine_FLIRT(transform_forward, transform_inverse, command_base)
        
    else:
        transform_complete=ants_registration_quick(input_file,ref_file, transform, command_base)

    return {
        "out_file":out_file,
        "output_dir":output_dir,
        "out_files": transform_complete["forward"],
        "transforms" : transform_complete
    }



class registrationInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_file = File(mandatory=True,desc="moving file")
    ref_file = File(mandatory=False,desc="reference file")
    registration_type = traits.String(mandatory=False,desc='registration type')

class registrationOutputSpec(TraitedSpec):
    out_file = File(desc='registered file')
    output_dir = traits.String(desc="Transform output directory")
    out_files = traits.List(desc='list of files')
    transforms = traits.Dict(desc='Transform Dictionary')
    
class registration_pan(BaseInterface):
    input_spec = registrationInputSpec
    output_spec = registrationOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = registration_proc(
            self.inputs.labels_dict,
            self.inputs.input_file,
            self.inputs.ref_file,
            self.inputs.registration_type,
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="registration_node",input_file="",ref_file="",registration_type="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(registration_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.input_file =  input_file       
    pan_node.inputs.ref_file =  ref_file
    pan_node.inputs.registration_type =  registration_type

    return pan_node


