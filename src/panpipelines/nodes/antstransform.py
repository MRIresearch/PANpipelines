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

def antstransform_proc(labels_dict,input_file,trans_mat,ref_file):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir = cwd

    command_base, container = getContainer(labels_dict,nodename="antstransform",SPECIFIC="ANTS_CONTAINER",LOGGER=IFLOGGER)
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
            os.makedirs(mgzdir)

        fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
        input_file_nii = newfile(mgzdir,input_file,extension=".nii.gz")
        convMGZ2NII(input_file, input_file_nii, fs_command_base)
        input_file = input_file_nii

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    work_dir = os.path.join(cwd,'{}_workdir'.format(participant_label))
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir)

    if isinstance(trans_mat[0],list):
        trans_parts = substitute_labels(trans_mat[0][-1],labels_dict).split(":")
    else:
        trans_parts = substitute_labels(trans_mat[-1],labels_dict).split(":")
    if len(trans_parts)>3:
        trans_mat_last = trans_parts[3]
    else:
        trans_mat_last = trans_parts[0]

    trans_mat_basename = os.path.basename(trans_mat_last)
    find_new_space = trans_mat_basename.split("_to-")
    if len(find_new_space) > 1:
        trans_space="space-"+trans_mat_basename.split("_to-")[1].split("_")[0] 
    else:
        trans_space=trans_mat_basename.split(".")[0]


    input_file_basename = os.path.basename(input_file)
    find_old_space=input_file_basename.split("_space-")
    if len(find_old_space) > 1:
        old_space="space-" + input_file_basename.split("_space-")[1].split("_")[0].split('.')[0] 
    else:
        old_space=None

    
    if old_space:
        out_file = os.path.join(output_dir,input_file_basename.replace(old_space, trans_space))
    else:
        out_file = newfile(output_dir,input_file_basename,intwix=trans_space)

    #ensure extension set to nifti
    out_file = newfile(assocfile=out_file,extension=".nii.gz")

    costfunction = getParams(labels_dict,'COST_FUNCTION')
    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    output_type = getParams(labels_dict,'OUTPUT_TYPE')


    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")


    transform_list=[]
    reverse_list=[]
    trans_ori = "RAS"

    for trans in trans_mat:
        # check if list passed within list then force to be single string item
        if isinstance(trans,list):
            trans = trans[0]
        trans_parts = trans.split(":")
        transform = getGlob(substitute_labels(trans_parts[0],labels_dict))
        trans_type =""
        trans_source = ""
        trans_reference = ""
        trans_reverse =  ""

        if len(trans_parts) == 6:
            trans_type = trans_parts[1]
            trans_source = substitute_labels(trans_parts[2],labels_dict)
            trans_reference = substitute_labels(trans_parts[3],labels_dict)
            trans_reverse = trans_parts[4]
            trans_ori = trans_parts[5]
        elif len(trans_parts) == 5:
            trans_type = trans_parts[1]
            trans_source = substitute_labels(trans_parts[2],labels_dict)
            trans_reference = substitute_labels(trans_parts[3],labels_dict)
            trans_reverse = trans_parts[4]
        elif len(trans_parts) == 4:
            trans_type = trans_parts[1]
            trans_source = substitute_labels(trans_parts[2],labels_dict)
            trans_reference = substitute_labels(trans_parts[3],labels_dict)
        elif len(trans_parts) == 3:
            trans_type = trans_parts[1]
            trans_source = substitute_labels(trans_parts[2],labels_dict)
        elif len(trans_parts) == 2:
            trans_type = trans_parts[1]

        if trans_reverse:
            if trans_reverse == "True":
                reverse_list.append(True)
            else:
                reverse_list.append(False)

        else:
            reverse_list.append(False)

        TRANSLIT="from-MNI152NLin6Asym_to-MNI152NLin2009cAsym"
        if TRANSLIT in str(transform):
            # if ref file not defined then assume that user implies this as reference
            if not ref_file:
                ref_file = TRANSLIT.split("_to-")[1]

            transform = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",suffix="xfm",extension=[".h5"])

        TRANSLIT="from-MNI152NLin2009cAsym_to-MNI152NLin6Asym"
        if TRANSLIT in str(transform):
            # if ref file not defined then assume that user implies this as reference
            if not ref_file:
                ref_file = TRANSLIT.split("_to-")[1]

            transform = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",suffix="xfm",extension=[".h5"])

        if transform == "tkregister2_fslout":
            new_freesurfer_transform = newfile(work_dir,transform,suffix="fsl-transform")
            fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
            tkregister2_fslout(trans_source,trans_reference, fs_command_base,new_freesurfer_transform)
            transform = new_freesurfer_transform

        if trans_type == "FSL":
            
            if pathlib.Path(transform).suffix == ".gz":
                # if we need the inverse of non-linear transform FSL transform then do that first before converting to ANTS and then reset reverse:
                if reverse_list[-1]==True:
                    new_transform = newfile(work_dir,transform,suffix="desc-inverse",extension=".nii.gz")
                    fsl_command_base, fslcontainer = getContainer(labels_dict,nodename="invertWarpfield_FNIRT",SPECIFIC="FSL_CONTAINER",LOGGER=IFLOGGER)
                    invertWarpfield_FNIRT(trans_source, transform, new_transform ,fsl_command_base)
                    transform = new_transform
                    reverse_list[-1]=False
                    trans_source = trans_reference

                new_ants_transform=newfile(work_dir,transform,suffix="ants-transform", extension=".nii.gz")
                wb_command_base, wbcontainer = getContainer(labels_dict,nodename="convertwarp_toANTS",SPECIFIC="WB_CONTAINER",LOGGER=IFLOGGER)
                convertwarp_toANTS(transform,trans_source, new_ants_transform, wb_command_base )
            else:
                new_ants_transform=newfile(work_dir,transform,suffix="ants-transform", extension=".mat")
                convert_affine_fsl_to_ants(transform, trans_source, trans_reference, new_ants_transform)
            transform = new_ants_transform
        
        transform_list.append(transform)

    # Process Reference_file
    ref_parts = ref_file.split(":")
    ref_file = getGlob(ref_parts[0])
    new_ref_file = newfile(work_dir,ref_file,suffix="desc-resample")

    REFLIT="MNI152NLin2009cAsym_res-"
    if REFLIT in str(ref_file):
        resolution=int(ref_file.split(REFLIT)[1])
        ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

    REFLIT="MNI152NLin6Asym_res-"
    if REFLIT in str(ref_file):
        resolution=int(ref_file.split(REFLIT)[1])
        ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

    if len(ref_parts) == 5:
        newdims_parts = ref_parts[1].split("|")
        newdims = newdims_parts[0]
        if len(newdims_parts) > 1:
            dim_type = newdims_parts[1]
        else:
            dim_type = ""
        ref_ori = ref_parts[2]
        interpolation_type = ref_parts[3]
        output_type = ref_parts[4]
        IFLOGGER.info("Calling function resampleimage_ants_ori with parameters:")
        IFLOGGER.info(f"input_file: {ref_file}")
        IFLOGGER.info(f"out_file: {new_ref_file}")
        IFLOGGER.info(f"newdims: {newdims}")
        IFLOGGER.info(f"dim_type: {dim_type}")
        IFLOGGER.info(f"ref_ori: {ref_ori}")
        IFLOGGER.info(f"interpolation_type: {interpolation_type}")
        IFLOGGER.info(f"output_type: {output_type:}")
        new_ref_file = resampleimage_ants_ori(ref_file,new_ref_file,newdims,command_base,dim_type=dim_type, target_ori=ref_ori,interpolation_type=interpolation_type,output_type=output_type)

    elif len(ref_parts) == 4:
        newdims_parts = ref_parts[1].split("|")
        newdims = newdims_parts[0]
        if len(newdims_parts) > 1:
            dim_type = newdims_parts[1]
        else:
            dim_type = ""
        ref_ori = ref_parts[2]
        interpolation_type = ref_parts[3]
        IFLOGGER.info("Calling function resampleimage_ants_ori with parameters:")
        IFLOGGER.info(f"input_file: {ref_file}")
        IFLOGGER.info(f"out_file: {new_ref_file}")
        IFLOGGER.info(f"newdims: {newdims}")
        IFLOGGER.info(f"dim_type: {dim_type}")
        IFLOGGER.info(f"ref_ori: {ref_ori}")
        IFLOGGER.info(f"interpolation_type: {interpolation_type}")
        new_ref_file = resampleimage_ants_ori(ref_file,new_ref_file,newdims,command_base,dim_type=dim_type,target_ori=ref_ori,interpolation_type=interpolation_type)
    
    elif len(ref_parts) == 3:
        newdims_parts = ref_parts[1].split("|")
        newdims = newdims_parts[0]
        if len(newdims_parts) > 1:
            dim_type = newdims_parts[1]
        else:
            dim_type = ""
        ref_ori = ref_parts[2]
        IFLOGGER.info("Calling function resampleimage_ants_ori with parameters:")
        IFLOGGER.info(f"input_file: {ref_file}")
        IFLOGGER.info(f"out_file: {new_ref_file}")
        IFLOGGER.info(f"newdims: {newdims}")
        IFLOGGER.info(f"dim_type: {dim_type}")
        IFLOGGER.info(f"ref_ori: {ref_ori}")
        new_ref_file = resampleimage_ants_ori(ref_file,new_ref_file,newdims,command_base,dim_type=dim_type,target_ori=ref_ori)

    elif len(ref_parts) == 2:
        newdims_parts = ref_parts[1].split("|")
        newdims = newdims_parts[0]
        if len(newdims_parts) > 1:
            dim_type = newdims_parts[1]
        else:
            dim_type = ""
        IFLOGGER.info("Calling function resampleimage_ants_ori with parameters:")
        IFLOGGER.info(f"input_file: {ref_file}")
        IFLOGGER.info(f"out_file: {new_ref_file}")
        IFLOGGER.info(f"newdims: {newdims}")
        IFLOGGER.info(f"dim_type: {dim_type}")
        new_ref_file = resampleimage_ants_ori(ref_file,new_ref_file,newdims,command_base,dim_type=dim_type,)

    if os.path.exists(new_ref_file):
        ref_file = new_ref_file

    IFLOGGER.info("Calling function apply_transform_ants_ori with parameters:")
    IFLOGGER.info(f"input_file: {input_file}")
    IFLOGGER.info(f"ref_file: {ref_file}")
    IFLOGGER.info(f"out_file: {out_file}")
    IFLOGGER.info(f"transform_list: {transform_list}")
    IFLOGGER.info(f"target_ori: {trans_ori}")
    IFLOGGER.info(f"costfunction: {costfunction}")
    IFLOGGER.info(f"output_type: {output_type}")
    IFLOGGER.info(f"reverse_list: {reverse_list}")

    apply_transform_ants_ori(input_file,
                            ref_file,
                            out_file,
                            transform_list,
                            command_base,
                            target_ori=trans_ori,                                              
                            costfunction=costfunction,
                            output_type=output_type,
                            reverse=reverse_list)

    out_files=[]
    out_files.insert(0,out_file)


    return {
        "out_file":out_file,
        "output_dir":output_dir,
        "out_files":out_files
    }



class antstransformInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_file = File(mandatory=True,desc="Image file to transform")
    trans_mat = traits.List(desc='list of transforms')
    ref_file = File(mandatory=False,desc="Image file to transform")

class antstransformOutputSpec(TraitedSpec):
    out_file = File(desc='transformed file')
    output_dir = traits.String(desc="Transform output directory")
    out_files = traits.List(desc='list of files')
    
class antstransform_pan(BaseInterface):
    input_spec = antstransformInputSpec
    output_spec = antstransformOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = antstransform_proc(
            self.inputs.labels_dict,
            self.inputs.input_file,
            self.inputs.trans_mat,
            self.inputs.ref_file
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="antstransform_node",input_file="",trans_mat="",ref_file="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(antstransform_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.input_file =  input_file       
    pan_node.inputs.trans_mat =  trans_mat
    pan_node.inputs.ref_file =  ref_file

    return pan_node


