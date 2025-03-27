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
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir = cwd
 
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    atlas_name = getParams(labels_dict,'NEWATLAS_NAME')
    atlas_workdir = os.path.join(cwd,'{}_workdir'.format(atlas_name))
    if not os.path.isdir(atlas_workdir):
        os.makedirs(atlas_workdir,exist_ok=True)

    atlas_file = newfile(cwd, atlas_name, prefix=f"sub-{participant_label}_ses-{participant_session}", extension="nii.gz")
    IFLOGGER.info(f"Creating new atlas {atlas_file}")

    special_atlas_type=""
    # scan through the roi list and find out if we have a special atlas type
    if roi_list[0].split(":")[0] == "special_atlas":
        special_atlas_type=roi_list[0].split(":")[1]


    atlas_type = getParams(labels_dict,'NEWATLAS_TYPE')
    if not atlas_type:
        atlas_type = "3D"

    prob_thresh =  getParams(labels_dict,'NEWATLAS_PROBTHRESH')
    if prob_thresh:
        if not isinstance(prob_thresh,list):
            prob_thresh = float(prob_thresh)
    else:
        prob_thresh = 0.5

    invert_roi =  getParams(labels_dict,'NEWATLAS_INVERTROI')
    if invert_roi:
        if not isinstance(invert_roi,list):
            invert_roi = isTrue(invert_roi)
    else:
        invert_roi = False

    atlas_index_mode = None
    if getParams(labels_dict,'NEWATLAS_INDEX_MODE'):
        atlas_index_mode = getParams(labels_dict,'NEWATLAS_INDEX_MODE')
    elif getParams(labels_dict,'ATLAS_INDEX_MODE'):
        atlas_index_mode = getParams(labels_dict,'ATLAS_INDEX_MODE')

    if special_atlas_type == "hcpmmp1aseg":
        roilabels_list=create_3d_hcpmmp1_aseg(atlas_file,roi_list,labels_dict)
        if not atlas_index_mode:
            atlas_index_mode = "hcpmmp1aseg_tsv"
        roi_list = [atlas_file]
    if special_atlas_type == "gmhemi" or special_atlas_type=="wmhemi" or special_atlas_type=="gmcort" or special_atlas_type=="wmintra" or special_atlas_type=="allhemi":
        roilabels_list=create_3d_hemi_aseg(atlas_file,roi_list,labels_dict,special_atlas_type)
        if not atlas_index_mode:
            atlas_index_mode = "freesurf_tsv_general"
        roi_list = [atlas_file]
    elif atlas_type == "3D":
        create_3d_atlas_from_rois(atlas_file, roi_list,labels_dict,prob_thresh=prob_thresh)
    elif atlas_type == "3D_contig":
        create_3d_atlas_from_rois(atlas_file, roi_list,labels_dict,prob_thresh=prob_thresh,explode3d=False)
    elif atlas_type == "3D_mask":
        roi_values = getParams(labels_dict,'MASK_ROIVALUE')
        create_3d_mask_from_rois(atlas_file, roi_list,labels_dict,roi_values=roi_values, prob_thresh=prob_thresh,explode3d=False,invert_roi=invert_roi)
    elif atlas_type =="4D_comprehensive":
        create_4d_atlas_from_rois(atlas_file, roi_list,labels_dict,low_thresh=prob_thresh)
    elif atlas_type =="4D":
        create_4d_atlas_from_rois(atlas_file, roi_list,labels_dict,low_thresh=prob_thresh,explode3d=False)
    else:
        create_3d_atlas_from_rois(atlas_file, roi_list,labels_dict,prob_thresh=prob_thresh)

    if not atlas_index_mode:
        atlas_index_mode = "tsv"

    if "tsv" in atlas_index_mode:
        atlas_index = newfile(cwd, atlas_name, prefix=f"sub-{participant_label}", suffix="dseg",extension="tsv")
    else:
        atlas_index = newfile(cwd, atlas_name, prefix=f"sub-{participant_label}",suffix="dseg", extension="txt")
    atlas_index_json = newfile(cwd,atlas_index,extension="json")
    IFLOGGER.info(f"Creating new atlas index {atlas_index}")
    atlas_index_out=""
    atlas_dict={}
    atlas_dict["Generator"]=roilabels_list
    with open(atlas_index,"w") as outfile:
        for roi_num in range(len(roilabels_list)):
            roiname=roilabels_list[roi_num]
            if roiname.split(":")[0] == "get_freesurfer_atlas_index":
                lutfile = substitute_labels(roiname.split(":")[1],labels_dict)

                atlas_dict,atlas_index_out=get_freesurferatlas_index_mode(roi_list[roi_num],lutfile,None,atlas_index_mode)
                atlas_dict["Generator"]=roilabels_list
                break
            if roiname.split(":")[0] == "generate_from_file":
                labelfile = substitute_labels(roiname.split(":")[1],labels_dict)
                with open(labelfile,"r") as infile:
                    atlas_index_out=infile.read()
                break
            elif roiname.split(":")[0] == "generate_from_rois":
                atlas_index_out = atlas_index_out + "index\tlabel\n"

                roi_num_x=0
                for roiname_x in roi_list:
                    if "tsv" in atlas_index_mode:
                        atlas_index_out = atlas_index_out + f"{roi_num_x + 1}\t{roiname_x}\n"
                    else:
                        atlas_index_out = atlas_index_out  + roiname_x + "\n"
                    roi_num_x=roi_num_x+1
                break

            else:
                if roi_num== 0 and "tsv" in atlas_index_mode:
                    atlas_index_out = atlas_index_out + "index\tlabel\n"

                if "tsv" in atlas_index_mode:
                    atlas_index_out = atlas_index_out + f"{roi_num + 1}\t{roiname}\n"
                else:
                    atlas_index_out = atlas_index_out  + roiname + "\n"
        outfile.write(atlas_index_out)
        export_labels(atlas_dict,atlas_index_json)

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


