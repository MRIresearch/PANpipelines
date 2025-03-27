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
from panpipelines.utils.report_functions import createRoiExtractReport

IFLOGGER=nlogging.getLogger('nipype.interface')

def roi_extract_proc(labels_dict,input_file,atlas_file,atlas_index, mask_file):

    metadata_comments=""
    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')

    USE_LABEL_SUBSET = isTrue(getParams(labels_dict,'USE_LABEL_SUBSET'))
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
        os.makedirs(roi_output_dir,exist_ok=True)

    if Path(atlas_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir,exist_ok=True)

        fs_command_base, fscontainer = getContainer(labels_dict,nodename="convMGZ2NII",SPECIFIC="FREESURFER_CONTAINER",LOGGER=IFLOGGER)
        atlas_file_nii = newfile(mgzdir,atlas_file,extension=".nii.gz")
        convMGZ2NII(atlas_file, atlas_file_nii, fs_command_base)
        atlas_file = atlas_file_nii

    if Path(input_file).suffix == ".mgz":
        mgzdir = os.path.join(cwd,'mgz_nii')
        if not os.path.isdir(mgzdir):
            os.makedirs(mgzdir,exist_ok=True)

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
            if not USE_LABEL_SUBSET:
                signals = extract_roi_mean_4D(input_file, atlas_img, mask_list=[mask_inverse_img])
            else:
                signals = extract_roi_mean_4D(input_file, atlas_img, mask_list=[mask_inverse_img],roi_list=labels_index_list)
        else:
            if not USE_LABEL_SUBSET:
                signals = extract_roi_mean_4D(input_file, atlas_img, mask_list=None)
            else:
                signals = extract_roi_mean_4D(input_file, atlas_img, mask_list=None,roi_list=labels_index_list)
        num_rows = signals.shape[0]

    else:
        if not USE_LABEL_SUBSET:
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
            NiftiMasker.fit(input_file)
            signals = NiftiMasker.transform(input_file)
            num_rows = signals.shape[0]
        else:
            if mask_inverse_img:
                signals = extract_roi_mean_3D(input_file, atlas_img, mask_list=[mask_inverse_img],roi_list=labels_index_list)
            else:
                signals = extract_roi_mean_3D(input_file, atlas_img, mask_list=None,roi_list=labels_index_list)
            num_rows = signals.shape[0]

    mask_inverse_file = None
    if mask_inverse_img:
        mask_inverse_file = newfile(roi_output_dir,input_file,prefix="nilearn-mask",suffix=MASK_NAME)
        nib.save(mask_inverse_img,mask_inverse_file)
    else:
        # find a better way e.g. by making the output spec non-mandatory
        # for now this is a horrible hack because previously passing "." causing havoc with DataSink
        mask_inverse_file =os.path.join(cwd,"placeholder.txt")
        with open(mask_inverse_file,"w") as outfile:
            outfile.write("Ignore this file. It is a placeholder for a non-existent mask file as a nipype workaround until better solution implemented.")

        

    # check that rois exist and check size of rois
    missing_rois = []
    unknown_rois=[]
    reconciled_labels = labels_name_list.copy()
    reconciled_signals = signals.copy()

    roi_sizes_list=[]
    roi_sizes_list.append(f"sub-{participant_label}")
    roi_sizes_list.append(f"ses-{session_label}")

    roi_sizes_masked_list=[]
    roi_sizes_masked_list.append(f"sub-{participant_label}")
    roi_sizes_masked_list.append(f"ses-{session_label}")

    roi_coverage_list=[]
    roi_coverage_list.append(f"sub-{participant_label}")
    roi_coverage_list.append(f"ses-{session_label}")

    roi_coverage_masked_list=[]
    roi_coverage_masked_list.append(f"sub-{participant_label}")
    roi_coverage_masked_list.append(f"ses-{session_label}")

    if atlas_type == "3D":
        atlas_data = atlas_img.get_fdata()
 
        for index in labels_index_list:
            lbl_index = labels_index_list.index(index)
            roi_sum = np.sum(atlas_data == int(index))
            roi_sizes_list.append(f"{str(roi_sum)}")

            if mask_inverse_img:
                roi_sum_masked = np.sum(np.logical_and(atlas_data == int(index), mask_inverse_img.get_fdata()))
                roi_sizes_masked_list.append(f"{str(roi_sum_masked)}")

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

            if mask_inverse_img:
                if measure_type == "3D":
                    check_masked = measure_data[np.logical_and(atlas_data == int(index), mask_inverse_img.get_fdata())]
                else:
                    check_masked = measure_data[np.logical_and(atlas_data == int(index), mask_inverse_img.get_fdata()),:]
                if len(check_masked) < 1:
                    roi_coverage_masked_list.append(f"0")
                else:
                    roi_coverage_masked = np.sum(check_masked != 0)
                    roi_coverage_masked_list.append(f"{str(roi_coverage_masked)}")

            if len(check) < 1:
                roi_coverage=0
                roi_coverage_list.append(f"{str(roi_coverage)}")
                UTLOGGER.warn(f"WARNING: Roi Number {index} does not have any values in the measures file  {input_file}.")
                UTLOGGER.warn(f"WARNING: Roi Number {index} corresponds with ROI name : {labels_name_list[lbl_index]}")
                # In future implement more sophisticated handling of missing labels
                #if lbl_index not in missing_rois:
                #    missing_rois.append(lbl_index)
                #    if num_rows > 1:
                #        insarr = np.array([np.nan for x in range(0,num_rows)])
                #        reconciled_signals= np.insert(reconciled_signals, lbl_index,[insarr],axis=1)
                #    else:
                #        reconciled_signals = np.insert(reconciled_signals,lbl_index,np.nan)
            else:
                roi_coverage = np.sum(check != 0)
                roi_coverage_list.append(f"{str(roi_coverage)}")

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
        if not labels_len == atlas_dim and not USE_LABEL_SUBSET:
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

        if not USE_LABEL_SUBSET:
            num_rois = atlas_img.shape[3]
            roi_choice = range(1,num_rois+1)
        else:
            roi_choice = labels_index_list
        atlas_data = atlas_img.get_fdata()

        for index in roi_choice:
            atlas_roi = atlas_data[...,index-1]
            lbl_index = labels_index_list.index(index)
            roi_sum = np.sum(atlas_roi > 0)
            roi_sizes_list.append(f"{str(roi_sum)}")

            if mask_inverse_img:
                roi_sum_masked = np.sum(np.logical_and(atlas_roi > 0, mask_inverse_img.get_fdata()))
                roi_sizes_masked_list.append(f"{str(roi_sum_masked)}")

            if measure_type == "3D":
                check = measure_data[atlas_roi > 0]               
            else:
                check = measure_data[atlas_roi > 0,:]

            if mask_inverse_img:
                if measure_type == "3D":
                    check_masked = measure_data[np.logical_and(atlas_roi > 0, mask_inverse_img.get_fdata())]
                else:
                    check_masked = measure_data[np.logical_and(atlas_roi > 0, mask_inverse_img.get_fdata()),:]
                if len(check_masked) < 1:
                    roi_coverage_masked_list.append(f"0")
                else:
                    roi_coverage_masked = np.sum(check_masked != 0)
                    roi_coverage_masked_list.append(f"{str(roi_coverage_masked)}")

            if len(check) < 1:
                roi_coverage=0
                roi_coverage_list.append(f"{str(roi_coverage)}")
                # In future implement more sophisticated handling of missing labels
                #print(f"WARNING: Atlas Roi Volume {lbl_index-1} does not have any values in the measures file {input_file}.")
                #missing_rois.insert(lbl_index-1,lbl_index)
                #if num_rows > 1:
                #    insarr = np.array([np.nan for x in range(0,num_rows)])
                #    reconciled_signals= np.insert(reconciled_signals, lbl_index-1,[insarr],axis=1)
                #else:
                #    reconciled_signals = np.insert(reconciled_signals,lbl_index-1,np.nan)
            else:
                roi_coverage = np.sum(check != 0)
                roi_coverage_list.append(f"{str(roi_coverage)}")   
    
   

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

    roi_csv = newfile(outputdir=roi_output_dir,assocfile=csv_basename,suffix="measures",extension="csv")

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
        last_df = df2

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
        last_df = newdf

    created_datetime = get_datetimestring_utc()
    last_df.insert(len(last_df.columns),"row_creation_datetime",[created_datetime for x in range(len(last_df))])
    last_df.to_csv(roi_csv,sep=",",header=True, index=False)

    roi_csv_sizes = newfile(outputdir=roi_output_dir,assocfile=csv_basename,suffix="roisizes",extension="csv")
    sizes_df=pd.DataFrame([roi_sizes_list],columns=["subject_id","session_id"]+[f"{atlas_name}.{x}" for x in labels_name_list])
    sizes_df.to_csv(roi_csv_sizes,sep=",",header=True, index=False)

    roi_csv_coverage = newfile(outputdir=roi_output_dir,assocfile=csv_basename,suffix="roicoverage",extension="csv")
    cov_df=pd.DataFrame([roi_coverage_list],columns=["subject_id","session_id"]+[f"{atlas_name}.{x}" for x in labels_name_list])
    cov_df.to_csv(roi_csv_coverage,sep=",",header=True, index=False)

    if mask_inverse_img:
        roi_csv_masked_sizes = newfile(outputdir=roi_output_dir,assocfile=csv_basename,suffix="desc-masked_roisizes",extension="csv")
        sizes_df=pd.DataFrame([roi_sizes_masked_list],columns=["subject_id","session_id"]+[f"{atlas_name}.{x}" for x in labels_name_list])
        sizes_df.to_csv(roi_csv_masked_sizes,sep=",",header=True, index=False)
        roi_csv_sizes=roi_csv_masked_sizes 

        roi_csv_masked_coverage = newfile(outputdir=roi_output_dir,assocfile=csv_basename,suffix="desc-masked_roicoverage",extension="csv")
        cov_df=pd.DataFrame([roi_coverage_masked_list],columns=["subject_id","session_id"]+[f"{atlas_name}.{x}" for x in labels_name_list])
        cov_df.to_csv(roi_csv_masked_coverage,sep=",",header=True, index=False)
        roi_csv_coverage = roi_csv_masked_coverage

    metadata = {}
    metadata = updateParams(metadata,"Title","roi_extract")
    metadata = updateParams(metadata,"Description","Extract Measures from Image file using provided atlas.")
    metadata = updateParams(metadata,"Atlas File",atlas_file)
    metadata = updateParams(metadata,"Atlas Labels",atlas_index)
    metadata = updateParams(metadata,"Atlas Name",atlas_name)
    metadata = updateParams(metadata,"Input File",input_file)
    metadata = updateParams(metadata,"Command","Nilearn NiftiMasker")
    if mask_inverse_img:
        metadata = updateParams(metadata,"Mask",mask_inverse_file)
    if metadata_comments:
        metadata = updateParams(metadata,"Comments",metadata_comments)
    metadata = updateParams(metadata,"ROI Voxel Sizes",roi_csv_sizes)
    metadata = updateParams(metadata,"ROI Coverage",roi_csv_coverage)
    roi_csv_json = create_metadata(roi_csv, created_datetime, metadata = metadata)

    html_file_dir = os.path.join(os.path.basename(roi_output_dir),"html_report")
    html_file = newfile(outputdir=html_file_dir, assocfile = roi_csv, suffix="htmlreport",extension="html")

    analysis_level = getParams(labels_dict,"ANALYSIS_LEVEL")
    html_file = createRoiExtractReport(labels_dict,html_file, metadata,analysis_level=analysis_level)

    out_files=[]
    out_files.insert(0,roi_csv)
    out_files.insert(1,roi_csv_json)
    out_files.insert(2,mask_inverse_file)
    out_files.insert(3,html_file)
    out_files.insert(4,input_file)
    out_files.insert(5,atlas_file)
    out_files.insert(6,atlas_index)
    out_files.insert(7,roi_csv_sizes)
    out_files.insert(8,roi_csv_coverage)

    return {
        "roi_csv":roi_csv,
        "roi_csv_metadata":roi_csv_json,
        "mask_file" : mask_inverse_file,
        "html_file" : html_file,
        "measure_file" : input_file,
        "atlas_file" : atlas_file,
        "atlas_index" : atlas_index,
        "roi_csv_sizes": roi_csv_sizes,
        "roi_csv_coverage": roi_csv_coverage,
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
    roi_csv_metadata = File(desc='metadata of CSV file of results')
    mask_file = File(desc='mask file used for results')
    html_file = File(desc='html file used for results')
    measure_file = File(desc='measure file containing statistics')
    atlas_file = File(desc='atlas file used for roi parcellation')
    atlas_index = File(desc='atlas index used to identify rois')
    roi_csv_sizes = traits.String(desc='roi_csv_sizes')
    roi_csv_coverage = traits.String(desc='roi_csv_coverage')
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


