from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import os
import glob
import nibabel as nb
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def atlascreate_proc(labels_dict,roi_list,roilabels_list):

    cwd=os.getcwd()
    output_dir = cwd
 
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')

    atlas_name = getParams(labels_dict,'ATLAS_NAME')
    atlas_workdir = os.path.join(cwd,'{}_workdir'.format(atlas_name))
    if not os.path.isdir(atlas_workdir):
        os.makedirs(atlas_workdir)

    atlas_file = newfile(cwd, atlas_name, prefix=f"sub-{participant_label}", extension="nii.gz")
    IFLOGGER.info(f"Creating new atlas {atlas_file}")

    special_atlas_type=""
    # scan through the roi list and find out if we have a special atlas type
    if roi_list[0] == "hcpmmp1aseg":
        special_atlas_type="hcpmmp1aseg"


    atlas_type = "3D"
    atlas_type = getParams(labels_dict,'NEWATLAS_TYPE')
    if special_atlas_type == "hcpmmp1aseg":
        roilabels_list=create_3d_hcppmmp1_aseg(atlas_file,roi_list,labels_dict)
        roi_list = [atlas_file]
    elif atlas_type == "3D":
        create_3d_atlas_from_rois(atlas_file, roi_list,labels_dict)
    elif atlas_type == "3D_contig":
        create_3d_atlas_from_rois(atlas_file, roi_list,labels_dict,explode3d=False)
    elif atlas_type =="4D":
        create_4d_atlas_from_rois(atlas_file, roi_list,labels_dict)
    else:
        create_3d_atlas_from_rois(atlas_file, roi_list,labels_dict)

    atlas_index = newfile(cwd, atlas_name, prefix=f"sub-{participant_label}", extension="txt")
    IFLOGGER.info(f"Creating new atlas index {atlas_index}")
    with open(atlas_index,"w") as outfile:
        for roi_num in range(len(roilabels_list)):
            roiname=roilabels_list[roi_num]
            if roiname.split(":")[0] == "get_freesurfer_atlas_index":
                roi_atlas_file= roi_list[roi_num]
                lutfile = substitute_labels(roiname.split(":")[1],labels_dict)
                atlas_dict,atlas_index_out=get_freesurferatlas_index(roi_atlas_file,lutfile,None)
                outfile.write(atlas_index_out)
            else:
                outfile.write(roiname + "\n")

    out_files=[]
    out_files.insert(0,atlas_file)
    out_files.insert(0,atlas_index)


    return {
        "atlas_file":atlas_file,
        "atlas_index":atlas_index,
        "output_dir":output_dir,
        "out_files":out_files
    }



class atlascreateInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    roi_list = traits.List(desc='list of roi files')
    roilabels_list = traits.List(desc='list of labels')

class atlascreateOutputSpec(TraitedSpec):
    atlas_file = File(desc='new atlas file')
    atlas_index = File(desc='new atlas index file')
    output_dir = traits.String(desc="new atlas output directory")
    out_files = traits.List(desc='list of files')
    
class atlascreate_pan(BaseInterface):
    input_spec = atlascreateInputSpec
    output_spec = atlascreateOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = atlascreate_proc(
            self.inputs.labels_dict,
            self.inputs.roi_list,
            self.inputs.roilabels_list
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="atlascreate_node",roi_list="",roilabels_list="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(atlascreate_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.roi_list  =  roi_list
    pan_node.inputs.roilabels_list = roilabels_list

    return pan_node


