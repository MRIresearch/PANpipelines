from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import os
import glob
import nibabel as nb
import pathlib

def antstransform_proc(labels_dict,input_file,trans_mat,ref_file):

    cwd=os.getcwd()
    output_dir = cwd

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    work_dir = os.path.join(cwd,'{}_workdir'.format(participant_label))
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir)

    trans_parts = substitute_labels(trans_mat[-1],labels_dict).split(":")
    if len(trans_parts)>2:
        trans_mat_last = trans_parts[2]
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
        old_space="space-" + input_file_basename.split("_space-")[1].split("_")[0] 
    else:
        old_space=None

    
    if old_space is not None:
        out_file = os.path.join(output_dir,input_file_basename.replace(old_space, trans_space))
    else:
        out_file = newfile(output_dir,input_file_basename,intwix=trans_space)

    costfunction = getParams(labels_dict,'COST_FUNCTION')
    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    output_type = getParams(labels_dict,'OUTPUT_TYPE')


    NEURO_CONTAINER = getParams(labels_dict,'NEURO_CONTAINER')
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")


    transform_list=[]
    reverse_list=[]

    for trans in trans_mat:
        trans_parts = trans.split(":")
        transform = substitute_labels(trans_parts[0],labels_dict)
        trans_basename = os.path.basename(transform)
        trans_type =""
        trans_source = ""
        trans_reference = ""
        trans_reverse =  ""

        if len(trans_parts) == 5:
            trans_type = trans_parts[1]
            trans_source = substitute_labels(trans_parts[2],labels_dict)
            trans_reference = trans_parts[3]
            trans_reverse = trans_parts[4]
        elif len(trans_parts) == 4:
            trans_type = trans_parts[1]
            trans_source = substitute_labels(trans_parts[2],labels_dict)
            trans_reference = trans_parts[3]
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


               
        if transform == "from-MNI152NLin6Asym_to-MNI152NLin2009cAsym_res-1":
            resolution=1
            trans = get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",suffix="xfm",extension=[".h5"])
            #last_ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])
            transform_list.append(str(trans))
        elif trans_type == "FSL":
            new_ants_transform=newfile(work_dir,transform,suffix="ants-transform")
            if pathlib.Path(transform).suffix == ".gz":
                convertwarp_toANTS(transform,trans_source, new_ants_transform, NEURO_CONTAINER )
                transform_list.append(new_ants_transform)
            else:
                convert_affine_fsl_to_ants(transform, trans_source, trans_reference, new_ants_transform)
                transform_list.append(new_ants_transform)

    if ref_file == "MNI152NLin2009cAsym_res-1":
        resolution=1
        ref_file=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=resolution,suffix="T1w",extension=[".nii.gz"])



    apply_transform_ants_ori(input_file,
                            ref_file,
                            out_file,
                            transform_list,
                            NEURO_CONTAINER,                                              
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


def create(labels_dict,name="antstransform_node",input_file="",trans_mat="",ref_file=""):
    # Create Node
    pan_node = Node(antstransform_pan(), name=name)
    # Specify node inputs

    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.input_file =  input_file       
    pan_node.inputs.trans_mat =  trans_mat
    pan_node.inputs.ref_file =  ref_file

    return pan_node


