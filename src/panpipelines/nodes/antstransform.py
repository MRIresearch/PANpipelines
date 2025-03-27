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
            os.makedirs(mgzdir,exist_ok=True)

        fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
        input_file_nii = newfile(mgzdir,input_file,extension=".nii.gz")
        convMGZ2NII(input_file, input_file_nii, fs_command_base)
        input_file = input_file_nii

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    work_dir = os.path.join(cwd,'{}_workdir'.format(participant_label))
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir,exist_ok=True)

    if isinstance(trans_mat[0],list):
        trans_mat = trans_mat[0]
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
    out_file = newfile(assocfile=out_file,prefix=f"sub-{participant_label}_ses-{participant_session}",extension=".nii.gz")

    costfunction = getParams(labels_dict,'COST_FUNCTION')
    fsl_costfunction = "sinc"
    if costfunction is None:
        costfunction="LanczosWindowedSinc"
    elif costfunction == "NearestNeighbor":
        fsl_costfunction = "nn"
        fsl_affine_costfunction="nearestneighbour"
    elif costfunction == "Linear":
        fsl_costfunction="trilinear"
        fsl_affine_costfunction="trilinear"
    elif costfunction == "Bspline":
        fsl_costfunction="spline"
        fsl_affine_costfunction="spline"

    output_type = getParams(labels_dict,'OUTPUT_TYPE')

    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")

    BYPASS_ANTS=False
    fsl_command_base, fslcontainer = getContainer(labels_dict,nodename="invertWarpfield_FNIRT",SPECIFIC="FSL_CONTAINER",LOGGER=IFLOGGER)
    fslwarp_dict={}

    prematconcat_list=[]
    fslaffineconcat_list=[]
 
    transform_list=[]
    reverse_list=[]
    trans_ori = ""
    transform_ori_src = ""
    transform_ori_ref = ""
    transform_target_ori=""

    ori_src = ""
    ori_ref = ""
    ori_targ= ""

    trans_num = len(trans_mat)
    trans_count = 1

    for trans in trans_mat:
        APPEND_TO_TRANSFORM_LIST=True
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

        if trans_ori:
            trans_ori_list=trans_ori.split("^")
            if len(trans_ori_list)>2:
                transform_ori_src=trans_ori_list[0]
                transform_ori_ref=trans_ori_list[1]
                transform_target_ori=trans_ori_list[2]
            elif len(trans_ori_list)>1:
                transform_ori_src=trans_ori_list[0]
                transform_ori_ref=trans_ori_list[1]
                transform_target_ori=""
            else:
                transform_ori_src=trans_ori_list[0]
                transform_ori_ref=""
                transform_target_ori=""
        else:
            transform_ori_src=""
            transform_ori_ref=""
            transform_target_ori=""
        
        if trans_reference:
            rf_or = get_orientation_from_file(trans_reference,"image")
            if rf_or:
                orig_trans_ref_ori = rf_or[0]
            else:
                orig_trans_ref_ori=""
        else:
            orig_trans_ref_ori=""

        if trans_source:    
            src_or= get_orientation_from_file(trans_source,"image")
            if src_or:
                orig_trans_src_ori = src_or[0]
            else:
                orig_trans_src_ori = ""
        else:
            orig_trans_src_ori=""

        # for situation where we are just using identity for 1 transform
        if transform=="identity" and trans_num == 1:
            if not transform_ori_ref:
                transform_ori_ref="RAS"
            if not transform_ori_src:
                transform_ori_src="RAS"
            if not transform_target_ori:
                input_ori =  get_orientation_from_file(input_file,"image")
                transform_target_ori=input_ori[0]

                
        TRANSLIT="from-MNI152NLin6Asym_to-MNI152NLin2009cAsym"
        if str(transform).startswith(TRANSLIT):
            # if ref file not defined then assume that user implies this as reference
            if not ref_file:
                ref_file = TRANSLIT.split("_to-")[1]

            transform = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",suffix="xfm",extension=[".h5"])

        TRANSLIT="from-MNI152NLin2009cAsym_to-MNI152NLin6Asym"
        if str(transform).startswith(TRANSLIT):
            # if ref file not defined then assume that user implies this as reference
            if not ref_file:
                ref_file = TRANSLIT.split("_to-")[1]

            transform = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",suffix="xfm",extension=[".h5"])

        REFLIT="MNI152NLin2009cAsym_res-"
        if str(trans_reference).startswith(REFLIT):
            resolution=int(trans_reference.split(REFLIT)[1])
            trans_reference=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

        if str(trans_source).startswith(REFLIT):
            resolution=int(trans_source.split(REFLIT)[1])
            trans_reference=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

        REFLIT="MNI152NLin6Asym_res-"
        if str(trans_reference).startswith(REFLIT):
            resolution=int(trans_reference.split(REFLIT)[1])
            ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

        if str(trans_source).startswith(REFLIT):
            resolution=int(trans_source.split(REFLIT)[1])
            ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

        if transform == "tkregister2_fslout":
            new_freesurfer_transform = newfile(work_dir,transform,suffix="fsl-transform")
            fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
            tkregister2_fslout(trans_source,trans_reference, fs_command_base,new_freesurfer_transform)
            transform = new_freesurfer_transform

        if trans_type == "FSL":
            if transform_ori_ref and orig_trans_ref_ori and not orig_trans_ref_ori == transform_ori_ref:
                print(f"reorienting  ref_file {trans_reference} from ref_ori {orig_trans_ref_ori} to expected_ref_ori {transform_ori_ref}")
                trans_reference=reorient(trans_reference, transform_ori_ref, cwd)

            if transform_ori_src and  orig_trans_src_ori and not orig_trans_src_ori == transform_ori_src:
                print(f"reorienting  stc_file {trans_source} from ref_ori {orig_trans_src_ori} to expected_ref_ori {transform_ori_src}")
                trans_source=reorient(trans_source, transform_ori_src, cwd)
            
            if pathlib.Path(transform).suffix == ".gz":
                # if we need the inverse of non-linear transform FSL transform then do that first before converting to ANTS and then reset reverse:
                if reverse_list[-1]==True:
                    new_transform = newfile(work_dir,transform,suffix="desc-inverse",extension=".nii.gz")
                    fsl_command_base, fslcontainer = getContainer(labels_dict,nodename="invertWarpfield_FNIRT",SPECIFIC="FSL_CONTAINER",LOGGER=IFLOGGER)
                    invertWarpfield_FNIRT(trans_source, transform, new_transform ,fsl_command_base)
                    transform = new_transform
                    reverse_list[-1]=False
                    trans_temp = trans_source
                    trans_source = trans_reference
                    trans_reference = trans_temp

                    transform_ori_temp=transform_ori_src
                    transform_ori_src=transform_ori_ref
                    transform_ori_ref=transform_ori_temp

                    orig_trans_temp =orig_trans_src_ori
                    orig_trans_src_ori =orig_trans_ref_ori
                    orig_trans_ref_ori=orig_trans_temp

                new_ants_transform=newfile(work_dir,transform,suffix="ants-transform", extension=".nii.gz")
                wb_command_base, wbcontainer = getContainer(labels_dict,nodename="convertwarp_toANTS",SPECIFIC="WB_CONTAINER",LOGGER=IFLOGGER)
                convertwarp_toANTS(transform,trans_source, new_ants_transform, wb_command_base )
            else:
                new_ants_transform=newfile(work_dir,transform,suffix="ants-transform", extension=".mat")
                convert_affine_fsl_to_ants(transform, trans_source, trans_reference, new_ants_transform)
            transform = new_ants_transform
        
        elif trans_type:
            BYPASS_ANTS=True
            if pathlib.Path(transform).suffix == ".gz":

                if "^ants_to_fsl" in trans_type:
                    new_fsl_transform=newfile(work_dir,transform,suffix="fsl-transform", extension=".nii.gz")
                    convertWarp_toFNIRT(transform, new_fsl_transform , trans_source, wb_command_base)
                    transform = new_fsl_transform

                # if we need the inverse of non-linear transform FSL transform then do that 
                if reverse_list[-1]==True:
                    new_transform = newfile(work_dir,transform,suffix="desc-inverse",extension=".nii.gz")
                    invertWarpfield_FNIRT(trans_source, transform, new_transform ,fsl_command_base)
                    transform = new_transform
                    reverse_list[-1]=False
                    trans_temp = trans_source
                    trans_source = trans_reference
                    trans_reference = trans_temp

                    transform_ori_temp=transform_ori_src
                    transform_ori_src=transform_ori_ref
                    transform_ori_ref=transform_ori_temp

                    orig_trans_temp =orig_trans_src_ori
                    orig_trans_src_ori =orig_trans_ref_ori
                    orig_trans_ref_ori=orig_trans_temp
            else:

                if "^ants_to_fsl" in trans_type:
                    new_fsl_transform=newfile(work_dir,transform,suffix="fsl-transform")
                    convert_affine_ants_to_fsl(transform, trans_source, trans_reference, new_fsl_transform)
                    transform = new_fsl_transform

                if reverse_list[-1]==True:
                    new_transform = newfile(work_dir,transform,suffix="desc-inverse")
                    invertAffine_FLIRT(transform, new_transform, fsl_command_base)
                    transform = new_transform
                    reverse_list[-1]=False
                    trans_temp = trans_source
                    trans_source = trans_reference
                    trans_reference = trans_temp

                    transform_ori_temp=transform_ori_src
                    transform_ori_src=transform_ori_ref
                    transform_ori_ref=transform_ori_temp

                    orig_trans_temp =orig_trans_src_ori
                    orig_trans_src_ori =orig_trans_ref_ori
                    orig_trans_ref_ori=orig_trans_temp

            if trans_type.startswith("premat_concat"):
                APPEND_TO_TRANSFORM_LIST = False
                prematconcat_list.append(transform)
            elif trans_type.startswith("fsl_affine_concat"):
                APPEND_TO_TRANSFORM_LIST = False
                fslaffineconcat_list.append(transform)                
            else:
                fslwarp_dict = updateParams(fslwarp_dict,trans_type,transform)

        if APPEND_TO_TRANSFORM_LIST:
            transform_list.append(transform)


        if trans_count == 1:
            if transform_ori_src:
                ori_src = transform_ori_src
            elif orig_trans_src_ori:
                ori_src = orig_trans_src_ori
            else:
                ori_src = ""

        if trans_count == trans_num:
            if transform_ori_ref:
                ori_ref = transform_ori_ref
            elif orig_trans_ref_ori:
                ori_ref = orig_trans_ref_ori
            else:
                ori_ref = ""

    
        trans_count = trans_count + 1

    transform_ori = ori_src + ":" + ori_ref

    # Process Reference_file
    ref_parts = ref_file.split(":")
    ref_ori = ""
    ref_file = getGlob(ref_parts[0])
    new_ref_file = newfile(work_dir,ref_file,suffix="desc-resample")

    REFLIT="MNI152NLin2009cAsym_res-"
    if str(ref_file).startswith(REFLIT):
        resolution=int(ref_file.split(REFLIT)[1])
        ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])

    REFLIT="MNI152NLin6Asym_res-"
    if str(ref_file).startswith(REFLIT):
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

    if ref_file:
        or_rf = get_orientation_from_file(ref_file,"image")
        if or_rf:
            orig_ref_file_ori = or_rf[0]
        else:
            orig_ref_file_ori=""
    else:
        orig_ref_file_ori=""

    if ref_ori:
        target_ori = ref_ori
    elif orig_ref_file_ori:
        target_ori = orig_ref_file_ori
    else:
        target_ori  = ""
    

    IFLOGGER.info("Calling function apply_transform_ants_ori with parameters:")
    IFLOGGER.info(f"input_file: {input_file}")
    IFLOGGER.info(f"ref_file: {ref_file}")
    IFLOGGER.info(f"out_file: {out_file}")
    IFLOGGER.info(f"transform_list: {transform_list}")
    IFLOGGER.info(f"transform_ori: {transform_ori}")
    IFLOGGER.info(f"target_ori: {trans_ori}")
    IFLOGGER.info(f"costfunction: {costfunction}")
    IFLOGGER.info(f"output_type: {output_type}")
    IFLOGGER.info(f"reverse_list: {reverse_list}")


    if not BYPASS_ANTS:
        apply_transform_ants_ori(input_file,
                                ref_file,
                                out_file,
                                transform_list,
                                command_base,
                                transform_ori=transform_ori,
                                target_ori=target_ori,                                              
                                costfunction=costfunction,
                                output_type=output_type,
                                reverse=reverse_list)
    # Hack to fix issues with solely concatenated affines causing weird issues with convertwarp!
    elif fslaffineconcat_list:
        start_tran = os.path.basename(fslaffineconcat_list[0]).split(".")[0]
        end_tran = os.path.basename(fslaffineconcat_list[-1]).split(".")[0]
        new_affine_transform = newfile(work_dir,f"{participant_label}_{participant_session}_prematconcat_from-{start_tran}_to-{end_tran}",extension="mat")
        concatMultipleAffines_FLIRT(fslaffineconcat_list,new_affine_transform,fsl_command_base)

        applyAffine_flirt(input_file,ref_file,out_file,new_affine_transform,fsl_command_base,interp=fsl_affine_costfunction)
  

    else:
        combined_warp= newfile(work_dir,out_file,suffix="convert-warp",extension=".nii.gz")
        fslwarp_dict = updateParams(fslwarp_dict,"--ref",ref_file)
        fslwarp_dict = updateParams(fslwarp_dict,"--out",combined_warp)

        if prematconcat_list:
            start_tran = os.path.basename(prematconcat_list[0]).split(".")[0]
            end_tran = os.path.basename(prematconcat_list[-1]).split(".")[0]
            new_prematconcat_transform = newfile(work_dir,f"{participant_label}_{participant_session}_prematconcat_from-{start_tran}_to-{end_tran}",extension="mat")
            concatMultipleAffines_FLIRT(prematconcat_list,new_prematconcat_transform,fsl_command_base)
            fslwarp_dict = updateParams(fslwarp_dict,"--premat",new_prematconcat_transform)


        command=f"{fsl_command_base} convertwarp"\
            " "+get_fslparams(fslwarp_dict)
        evaluated_command=substitute_labels(command, labels_dict)
        runCommand(evaluated_command,IFLOGGER)

        fslwarp_dict = {}
        fslwarp_dict = updateParams(fslwarp_dict,"-i",input_file)
        fslwarp_dict = updateParams(fslwarp_dict,"-o",out_file)
        fslwarp_dict = updateParams(fslwarp_dict,"-r",ref_file)
        fslwarp_dict = updateParams(fslwarp_dict,"--interp",fsl_costfunction)
        fslwarp_dict = updateParams(fslwarp_dict,"-w",combined_warp)

        command=f"{fsl_command_base} applywarp"\
            " "+get_fslparams(fslwarp_dict)
        evaluated_command=substitute_labels(command, labels_dict)
        runCommand(evaluated_command,IFLOGGER)


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


