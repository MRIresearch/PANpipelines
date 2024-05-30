from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
import pandas as pd
import json
import datetime
from pathlib import Path
import shlex
import subprocess
from nipype import logging as nlogging
from nilearn.maskers import NiftiLabelsMasker
from nilearn.maskers import NiftiMapsMasker
from nilearn import image

IFLOGGER=nlogging.getLogger('nipype.interface')

def roi_extract_proc(labels_dict,input_file,atlas_file,atlas_index, mask_file):

    metadata_comments=""
    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')

    INVERT_MASK = isTrue(getParams(labels_dict,'MASK_INVERT'))
    MASK_NAME = getParams(labels_dict,'MASK_NAME')
    if not MASK_NAME:
        MASK_NAME = "mask"

    mask_img =None
    mask_inverse_img = None
    if mask_file and not mask_file == ".": 
        IFLOGGER.info(f"{mask_file} provided to mask measures.")
        mask_img = nib.load(mask_file)
        mask_data = mask_img.get_fdata()
        if INVERT_MASK:
            IFLOGGER.info(f"Inverse of {mask_file} will be used to mask results.")
            inverse_data = np.zeros(mask_data.shape)
            inverse_data[mask_data < 1] = 1 
            mask_inverse_img=nib.Nifti1Image(inverse_data, mask_img.affine)
        else:
            mask_inverse_img=mask_img

    
    if not session_label:
        roi_output_dir = os.path.join(cwd,f"sub-{participant_label}_roi_output_dir")
    else:
        roi_output_dir = os.path.join(cwd,f"sub-{participant_label}_ses-{session_label}_roi_output_dir")

    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    if Path(atlas_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir)

        fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
        atlas_file_nii = newfile(mgzdir,atlas_file,extension=".nii.gz")
        convMGZ2NII(atlas_file, atlas_file_nii, fs_command_base)
        atlas_file = atlas_file_nii

    if Path(input_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir)

        fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
        input_file_nii = newfile(mgzdir,input_file,extension=".nii.gz")
        convMGZ2NII(input_file, input_file_nii, fs_command_base)
        input_file = input_file_nii

    atlas_type="3D"
    atlas_img  = nib.load(atlas_file)
    atlas_dim = 1
    atlas_shape = atlas_img.header.get_data_shape()
    if len(atlas_shape) > 3:
        if atlas_shape[3]> 1:
            atlas_type="4D"
            atlas_dim = atlas_shape[3]

    atlas_index_mode = None
    if getParams(labels_dict,'ATLAS_INDEX_MODE'):
        atlas_index_mode = getParams(labels_dict,'ATLAS_INDEX_MODE')
    elif getParams(labels_dict,'NEWATLAS_INDEX_MODE'):
        atlas_index_mode = getParams(labels_dict,'NEWATLAS_INDEX_MODE')

    if not atlas_index_mode:
        atlas_index_mode = "tsv"
    
    check_unknown_rois = False
    if getParams(labels_dict,'CHECK_UNKNOWN_ROIS'):
        check_unknown_rois = isTrue(getParams(labels_dict,'CHECK_UNKNOWN_ROIS'))

    if atlas_index.split(":")[0] == "get_freesurfer_atlas_index":
        lutfile = substitute_labels(atlas_index.split(":")[1],labels_dict)
        if "tsv" in atlas_index_mode:
            new_atlas_index=newfile(roi_output_dir,atlas_file,suffix="desc-index",extension=".tsv")
        else:
            new_atlas_index=newfile(roi_output_dir,atlas_file,suffix="desc-index",extension=".txt")
        atlas_index_json = newfile(roi_output_dir,new_atlas_index,extension="json")
        atlas_dict,atlas_index_out=get_freesurferatlas_index_mode(atlas_file,lutfile,new_atlas_index,atlas_index_mode=atlas_index_mode)
        atlas_index=new_atlas_index
        export_labels(atlas_dict,atlas_index_json)

    # See if atlas index is in right format
    labelfile_df=pd.read_csv(atlas_index,delim_whitespace=True)
    if "index" in labelfile_df.columns and "label" in labelfile_df:
        labels_index_list = labelfile_df["index"].tolist()
        labels_name_list = labelfile_df["label"].tolist()
    else:
        with open(atlas_index, 'r') as in_file:
            lines = in_file.readlines()
        labels_name_list = [x.replace('\n','') for x in lines]
        labels_index_list = range(1,len(labels_name_list)+1)

    measure_type = "3D"
    measure_img = nib.load(input_file)
    measure_data = measure_img.get_fdata()
    measure_shape = measure_img.header.get_data_shape()
    if len(measure_shape) > 3:
        if measure_shape[3] > 1:
            measure_type = "4D"

    if atlas_type == "4D":
        if mask_inverse_img:
            NiftiMasker = NiftiMapsMasker(
                atlas_img,
                mask_img = mask_inverse_img,
                Labels = labels_name_list,
                standardize=False
            )
        else:
            NiftiMasker = NiftiMapsMasker(
                atlas_img,
                Labels = labels_name_list,
                standardize=False
            )
    else:
        if mask_inverse_img:
            NiftiMasker = NiftiLabelsMasker(
                atlas_img,
                mask_img = mask_inverse_img,
                Labels = labels_name_list,
                standardize=False
            )
        else:
            NiftiMasker = NiftiLabelsMasker(
                atlas_img,
                Labels = labels_name_list,
                standardize=False
            )

    mask_inverse_file = None
    if mask_inverse_img:
        mask_inverse_file = newfile(roi_output_dir,input_file,prefix="nilearn-mask",suffix=MASK_NAME)
        nib.save(mask_inverse_img,mask_inverse_file)

    NiftiMasker.fit(input_file)
    signals = NiftiMasker.transform(input_file)
    num_rows = signals.shape[0]

    # check that rois exist:
    missing_rois = []
    unknown_rois=[]
    reconciled_labels = labels_name_list.copy()
    reconciled_signals = signals.copy()
    if atlas_type == "3D":
        atlas_data = atlas_img.get_fdata()
 
        for index in labels_index_list:
            lbl_index = labels_index_list.index(index)
            roi_sum = np.sum(atlas_data == int(index))
            if roi_sum == 0:               
                UTLOGGER.warn(f"WARNING: Roi Number {index} is missing from atlas {atlas_file}. Have you provided the correct labels in {atlas_index} ?")
                UTLOGGER.warn(f"WARNING: Roi Number {index} corresponds with ROI name : {labels_name_list[lbl_index]}")               
                if lbl_index not in missing_rois:
                    missing_rois.append(lbl_index)
                    if num_rows > 1:
                        insarr = np.array([np.nan for x in range(0,num_rows)])
                        reconciled_signals= np.insert(reconciled_signals, lbl_index,[insarr],axis=1)
                    else:
                        reconciled_signals = np.insert(reconciled_signals,lbl_index,np.nan)

                        
        for index in labels_index_list:
            lbl_index = labels_index_list.index(index)
            if measure_type == "3D":
                check = measure_data[atlas_data == int(index)]
            else:
                check = measure_data[atlas_data == int(index),:]
            if len(check) < 1:
                UTLOGGER.warn(f"WARNING: Roi Number {index} does not have any values in the measures file  {input_file}.")
                UTLOGGER.warn(f"WARNING: Roi Number {index} corresponds with ROI name : {labels_name_list[lbl_index]}")
                if lbl_index not in missing_rois:
                    missing_rois.append(lbl_index)
                    if num_rows > 1:
                        insarr = np.array([np.nan for x in range(0,num_rows)])
                        reconciled_signals= np.insert(reconciled_signals, lbl_index,[insarr],axis=1)
                    else:
                        reconciled_signals = np.insert(reconciled_signals,lbl_index,np.nan)

        # check for unknown rois, assume rous start from 1 and indexing starts from zero
        if check_unknown_rois:
            max_roi = int(np.max(atlas_data))
            for roi_avail in range(1,max_roi+1):
                if roi_avail not in labels_index_list:
                    UTLOGGER.warn(f"WARNING: The roi label; {roi_avail} is present in the atlas but missing in the the index {atlas_index}. Have you provided the correct atlas {atlas_file}")
                    if f"{roi_avail}_unknown" not in unknown_rois:
                        unknown_rois.append(f"{roi_avail}_unknown")
                        reconciled_labels.insert(roi_avail - 1,f"{roi_avail}_unknown")
                        if num_rows > 1:
                            insarr = np.array([np.nan for x in range(0,num_rows)])
                            reconciled_signals= np.insert(reconciled_signals, roi_avail - 1,[insarr],axis=1)
                        else:
                            reconciled_signals = np.insert(reconciled_signals,roi_avail - 1,np.nan)

    else:
        labels_len = len(labels_name_list)
        if not labels_len == atlas_dim:
            UTLOGGER.warn(f"WARNING: Mismatch between number of labels {len(labels_name_list)} and the size of 4D atlas {atlas_dim}. Please correct this.")
            if labels_len  < atlas_dim:
                if check_unknown_rois:
                    UTLOGGER.warn(f"WARNING: There is/are {atlas_dim - labels_len} unknown roi/s.")
                    for unk in range(1,atlas_dim - labels_len + 1):
                        unknown_rois.append(f"unknown{unk}")
                        reconciled_labels.append(f"unknown{unk}")
            else:
                UTLOGGER.warn(f"WARNING: There is/are {labels_len - atlas_dim} missing roi/s.")
                for miss in range(atlas_dim,labels_len):
                    missing_rois.append(miss)
                    if num_rows > 1:
                        insarr = np.array([np.nan for x in range(0,num_rows)])
                        reconciled_signals= np.insert(reconciled_signals, len(reconciled_signals),[insarr],axis=1)
                    else:
                        reconciled_signals = np.insert(reconciled_signals,len(reconciled_signals[0]),np.nan)

        atlas_index=0
        for img in image.iter_img(atlas_img):
            atlas_data = img.get_fdata()
            if measure_type == "3D":
                check = measure_data[atlas_data > 0]               
            else:
                check = measure_data[atlas_data > 0,:]
            if len(check) < 1:
                print(f"WARNING: Atlas Roi Volume {atlas_index} does not have any values in the measures file {input_file}.")
                missing_rois.insert(atlas_index,atlas_index+1)
                if num_rows > 1:
                    insarr = np.array([np.nan for x in range(0,num_rows)])
                    reconciled_signals= np.insert(reconciled_signals, atlas_index,[insarr],axis=1)
                else:
                    reconciled_signals = np.insert(reconciled_signals,atlas_index,np.nan)
    
            atlas_index = atlas_index + 1       

    if len(reconciled_signals.shape) > 1:
        df2=pd.DataFrame(reconciled_signals,columns=reconciled_labels)
    else:
        df2=pd.DataFrame([reconciled_signals],columns=reconciled_labels)
    
    csv_basename = ""

    atlas_name = getParams(labels_dict,'ATLAS_NAME')
    if not atlas_name:
        atlas_name = getParams(labels_dict,'NEWATLAS_NAME')
    if not atlas_name:
        atlas_name = "-".join([x for x in os.path.basename(atlas_file).split("_") if not "sub" in x and not "ses" in x])
        atlas_name = atlas_name.split(".nii")[0]
    csv_basename = f"atlas-{atlas_name}"

    modality = get_bidstag("desc",input_file,True)
    if modality:
        modality=modality[-1].split(".")[0]
        csv_basename = csv_basename + "_" + modality
    else:
        modality = "-".join([x for x in os.path.basename(input_file).split("_") if not "sub" in x and not "ses" in x])
        modality = modality.split(".nii")[0]
        csv_basename = csv_basename + "_" + modality

    table_columns = [f"{atlas_name}.{modality}.{x}" for x in reconciled_labels]

    if not session_label:
        csv_basename  = f"sub-{participant_label}" + "_" + csv_basename
    else:
        csv_basename  = f"sub-{participant_label}_ses-{session_label}" + "_" + csv_basename

    roi_csv = newfile(outputdir=roi_output_dir,assocfile=csv_basename,extension="csv")

    if num_rows < 2:
        if session_label:
            df2.insert(0,"session_id",["ses-"+session_label])
            table_columns.insert(0,"session_id")
        else:
            df2.insert(0,"session_id",["NotProvided"])
            table_columns.insert(0,"session_id")

        df2.insert(0,"subject_id",["sub-"+participant_label])
        table_columns.insert(0,"subject_id")

        df2.columns = table_columns
        df2.to_csv(roi_csv,sep=",",header=True, index=False)
    else:
        flat_vals=[]
        flat_tablecolumns=[]
        for count in range(num_rows):
            flat_vals.extend(df2.iloc[count].to_list())
            flat_tablecolumns.extend([x + f".{count}" for x in table_columns])
        newdf=pd.DataFrame([flat_vals])
        if session_label:
            newdf.insert(0,"session_id",["ses-"+session_label])
            flat_tablecolumns.insert(0,"session_id")
        else:
            newdf.insert(0,"session_id",["NotProvided"])
            flat_tablecolumns.insert(0,"session_id")
        newdf.insert(0,"subject_id",["sub-"+participant_label])
        flat_tablecolumns.insert(0,"subject_id")
        newdf.columns = flat_tablecolumns
        newdf.to_csv(roi_csv,sep=",",header=True, index=False)


    metadata = {}
    roi_json = os.path.join(roi_output_dir,'{}.json'.format(csv_basename))
    metadata = updateParams(metadata,"Title","roi_extract")
    metadata = updateParams(metadata,"Description","Extract Measures from Image file using provided atlas.")
    metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
    metadata = updateParams(metadata,"Atlas File",atlas_file)
    metadata = updateParams(metadata,"Atlas Labels",atlas_index)
    metadata = updateParams(metadata,"Input File",input_file)
    metadata = updateParams(metadata,"Command","Nilearn NiftiMasker")
    if mask_inverse_file:
        metadata = updateParams(metadata,"Mask",mask_inverse_file)
    if metadata_comments:
        metadata = updateParams(metadata,"Comments",metadata_comments)

    export_labels(metadata,roi_json)


    out_files=[]
    out_files.insert(0,roi_csv)

    return {
        "roi_csv":roi_csv,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class roi_extractInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_file = File(desc="input file")
    atlas_file = File(desc='atlas file')
    atlas_index = File(desc='atlas index file')
    mask_file = File(desc='mask file')

class roi_extractOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    roi_output_dir = traits.String(desc='roi output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class roi_extract_pan(BaseInterface):
    input_spec = roi_extractInputSpec
    output_spec = roi_extractOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = roi_extract_proc(
            self.inputs.labels_dict,
            self.inputs.input_file,
            self.inputs.atlas_file,
            self.inputs.atlas_index,
            self.inputs.mask_file,
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="roi_extract_node",input_file="",atlas_file="",atlas_index="", mask_file="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(roi_extract_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.input_file = input_file
    pan_node.inputs.atlas_file =  atlas_file
    pan_node.inputs.atlas_index =  atlas_index
    pan_node.inputs.mask_file =  mask_file

    return pan_node


