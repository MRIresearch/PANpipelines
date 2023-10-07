from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import nibabel as nb

def antstransform_proc(labels_dict,input_file,trans_mat,ref_file):

    cwd=os.getcwd()

    trans_mat_basename = os.path.basename(trans_mat)
    find_new_space = trans_mat_basename.split("_to-")
    if len(find_new_space) > 1:
        trans_space="_space-"+trans_mat_basename.split("_to-")[1].split("_mode")[0] + "_"
    else:
        trans_space=trans_mat_basename.split(".")[0]


    input_file_basename = os.path.basename(input_file)
    find_old_space=input_file_basename.split("_space-")
    if len(find_old_space) > 1:
        old_space="_space-" + input_file_basename.split("_space-")[1].split("_")[0] + "_"
    else:
        old_space=None

    output_dir = getParams(labels_dict,'CUSTOM_OUTPUT_DIR')
    if output_dir is None:
        output_dir = cwd


    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    if old_space is not None:
        out_file = os.path.join(output_dir,input_file_basename.replace(old_space, trans_space))
    else:
        out_file = os.path.join(output_dir,insert_bidstag("desc-"+trans_space, input_file_basename ))

    costfunction = getParams(labels_dict,'COST_FUNCTION')
    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    img = nb.load(input_file)
    dimz=1
    if len(img.header.get_data_shape()) > 3:
        dimz = img.header.get_data_shape()[3]

    image_type = 1
    if dimz > 1:
        image_type = 3
    
    # for labels, atlases consider -n NearestNeighbor
    params="-d 3" \
        " -e " + image_type +\
        " -i " + input_file +\
        " -f 0"\
        " --float 1"\
        " -n "+costfunction+\
        " -o "+ out_file +\
        " -r " + ref_file + \
        " -t " + trans_mat + \
        " -v 1"

    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> antsApplyTransforms"\
            " "+params

    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslreorient2std"\
            " "+out_file+" "+out_file
    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

    # quick hack to fix issue with mapnodes - 5 dims instead of 3 dims used in header
    command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslroi"\
            " "+out_file+" "+out_file + " 0 "+str(dimz)
    evaluated_command=substitute_labels(command, labels_dict)
    os.system(evaluated_command)

 
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
    trans_mat = File(mandatory=False,desc="Image file to transform")
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

    if trans_mat is None or trans_mat == "" or not os.path.isfile(trans_mat):
        trans_mat  = substitute_labels("<QSIPREP_TRANS_MAT>", labels_dict)

    if ref_file is None or ref_file == "" or not os.path.isfile(ref_file):
        ref_file = substitute_labels("<QSIPREP_REF_FILE>", labels_dict)
        
    pan_node.inputs.trans_mat =  trans_mat
    pan_node.inputs.ref_file =  ref_file

    return pan_node


