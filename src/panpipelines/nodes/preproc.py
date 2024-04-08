from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging
import json
import sys
import nibabel
from nibabel.affines import apply_affine 
import numpy as np
import numpy.linalg as npl
from scipy import ndimage 
from skimage import measure
import shutil
import panpipelines.scripts.pancontainer_panscript as pancontainer_script
import panpipelines.scripts.mne_make_surfaces as mne_make_surfaces
import mne
from panpipelines.nodes.antstransform import antstransform_proc

# simulate strel('disk',5);
disc5 = np.zeros((9,9,9))
disc5[2:7,0:,0:]=1
disc5[0,2:7,2:7]=1
disc5[-1,2:7,2:7]=1
disc5[1,1:-1,1:-1]=1
disc5[7,1:-1,1:-1]=1

# simulate strel('disk',2);
disc2 = np.zeros((5,5,5))
disc2[2,2,2]=1
disc2[4,4,4]=1
disc2[2,0:,0:]=1
disc2[1,1:4,1:4]=1
disc2[3,1:4,1:4]=1
# simulate strel('disk',3)
disc3 = np.ones((5,5,5))

streldict={
    "disc5" : disc5,
    "disc3" : disc3,
    "disc2" : disc2
}


IFLOGGER=nlogging.getLogger('nipype.interface')

def returnCandidates(p0,p1,p2):
    arrayList=[]
    max_x = np.max(np.array([p0[0],p1[0],p2[0]]))
    max_y = np.max(np.array([p0[1],p1[1],p2[1]]))
    max_z = np.max(np.array([p0[2],p1[2],p2[2]]))
    min_x = np.min(np.array([p0[0],p1[0],p2[0]]))
    min_y = np.min(np.array([p0[1],p1[1],p2[1]]))
    min_z = np.min(np.array([p0[2],p1[2],p2[2]]))
    for x in range(min_x,max_x+1):
        for y in range(min_y, max_y + 1):
            for z in range(min_z,max_z + 1):
                p = np.array([x,y,z])
                if validCandidate(p0,p1,p2,p,tol=0.15):
                    arrayList.append(p)
    return arrayList

#https://math.stackexchange.com/questions/2582202/does-a-3d-point-lie-on-a-triangular-plane
def validCandidate(p0,p1,p2,p,tol):
    n = np.cross(p1-p0,p2-p0)/npl.norm(np.cross(p1-p0,p2-p0))
    d = np.dot(n,p-p1)
    if np.abs(d) < tol:
        return True
    else:
        return False

def derive_asl_artefact_v2(asl_acq,labels_dict,command_base,participant_label,participant_session,artefact_outputdir,PHASESHIFT=12,PHASEAXIS=1,ALLOWOVERLAP=False,CLOSE_DISC=1,DILATE_DISC=2):
    
    transform_list =  getParams(labels_dict,'TRANSFORM_MAT')
    transform_ref =  getParams(labels_dict,'TRANSFORM_REF')
    PHASESHIFT_lookup = getParams(labels_dict,'PHASESHIFT')
    if PHASESHIFT_lookup:
        if isinstance(PHASESHIFT_lookup,dict):
            if asl_acq in PHASESHIFT_lookup.keys():
                PHASESHIFT=int(PHASESHIFT_lookup[asl_acq])
        else:
            PHASESHIFT = int(PHASESHIFT_lookup)
    if getParams(labels_dict,'PHASEAXIS'):
        PHASEAXIS = int(getParams(labels_dict,'PHASEAXIS'))
    if getParams(labels_dict,'CLOSE_DISC'):
        CLOSE_DISC = int(getParams(labels_dict,'CLOSE_DISC'))
    if getParams(labels_dict,'DILATE_DISC'):
        DILATE_DISC = int(getParams(labels_dict,'DILATE_DISC'))
    if getParams(labels_dict,'ALLOWOVERLAP'):
        ALLOWOVERLAP = isTrue(getParams(labels_dict,'ALLOWOVERLAP'))

    cwd = os.getcwd()
    output_dir=cwd

    work_dir=os.path.join(output_dir,"preproc_workdir")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    labels_dict = updateParams(labels_dict,"CWD",cwd)

    # set up dwi to process just the specific dwi session
    subject = f"sub-{participant_label}"
    if participant_session:
        session = f"ses-{participant_session}"
    else:
        session=""

    if not artefact_outputdir:
        artefact_outputdir = os.path.join(output_dir,"asl_artefact", subject,session)
    else:
        artefact_outputdir = os.path.join(artefact_outputdir,"asl_artefact", subject,session)

    if not os.path.exists(artefact_outputdir):
        os.makedirs(artefact_outputdir, exist_ok=True)


    subjects_dir = getParams(labels_dict,'SUBJECTS_DIR')
    outer_skull=os.path.join(subjects_dir,subject,'bem','outer_skull.surf')

    params =  f" --subject {subject}" \
            f" --subjects_dir {subjects_dir}" 
    PREPROC_CONTAINER_TO_USE = getParams(labels_dict,"PREPROC_CONTAINER_TO_USE")
    if PREPROC_CONTAINER_TO_USE:
        panscript = pancontainer_script.pancontainer_panscript(labels_dict,params=params,command=f"python {mne_make_surfaces.__file__}",container_img=PREPROC_CONTAINER_TO_USE)
    else: 
        panscript = pancontainer_script.pancontainer_panscript(labels_dict,params=params,command=f"python {mne_make_surfaces.__file__}")
    panscript.run()
    os.chdir(output_dir)

    rr_mm_outer_skull,tris_outer_skull = mne.read_surface(outer_skull)

    orig_file=f"{subjects_dir}/{subject}/mri/T1.mgz"
    origimg = nibabel.load(orig_file)
    Torig = origimg.header.get_vox2ras_tkr()
    origimg_dtype = origimg.header.get_data_dtype()
    origimg_shape = origimg.shape
    outer_skull_vol = np.zeros((origimg_shape),dtype=origimg_dtype)
    inv_Torig = npl.inv(Torig)

    for rr in rr_mm_outer_skull:
        vox = apply_affine(inv_Torig, rr)
        vox_ind = tuple(np.round(vox).astype(int))
        outer_skull_vol[vox_ind] = 255

    for tri in tris_outer_skull:
        p0 = np.round(apply_affine(inv_Torig,rr_mm_outer_skull[tri[0]])).astype(int)
        p1 = np.round(apply_affine(inv_Torig,rr_mm_outer_skull[tri[1]])).astype(int)
        p2 = np.round(apply_affine(inv_Torig,rr_mm_outer_skull[tri[2]])).astype(int)
        valid_vox = returnCandidates(p0,p1,p2)
        for vox in valid_vox:
            vox_ind = tuple(vox.astype(int))
            outer_skull_vol[vox_ind] = 255
    outer_skull_img = nibabel.Nifti1Image(outer_skull_vol,origimg.affine,origimg.header)
    outer_skull_img_file=os.path.join(work_dir,f"{subject}_{session}_outer_skull.nii.gz")
    nibabel.save(outer_skull_img,outer_skull_img_file) 

    outer_skull_aslspace_file = None
    if transform_list and transform_ref:
        results = antstransform_proc(labels_dict, outer_skull_img_file,transform_list, transform_ref)
        outer_skull_aslspace_file = results['out_file']     

    outer_skull_aslspace_bin=newfile(work_dir,outer_skull_aslspace_file,suffix="bin")
    command = f"{command_base} fslmaths {outer_skull_aslspace_file} -abs -bin {outer_skull_aslspace_bin}"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    outskull_aslspace_img=nibabel.load(outer_skull_aslspace_bin)
    outskull_aslspace_data = outskull_aslspace_img.get_fdata()
    outskull_aslspace_file  = outer_skull_aslspace_bin

    if DILATE_DISC > 0:
        disc = np.ones((DILATE_DISC,DILATE_DISC,DILATE_DISC))
        outskull_aslspace_data_dilation = ndimage.binary_dilation(outskull_aslspace_data, structure=disc).astype(np.int16)
        outskull_aslspace_data_dilation_file=newfile(work_dir,outskull_aslspace_file,suffix=f"dilation-disc-{DILATE_DISC}")
        outskull_aslspace_data_dilation_img = nibabel.Nifti1Image(outskull_aslspace_data_dilation,outskull_aslspace_img.affine,outskull_aslspace_img.header)
        nibabel.save(outskull_aslspace_data_dilation_img,outskull_aslspace_data_dilation_file)
        outskull_aslspace_file = outskull_aslspace_data_dilation_file
        outskull_aslspace_data = outskull_aslspace_data_dilation
    
    if CLOSE_DISC > 0:
        disc = np.ones((CLOSE_DISC,CLOSE_DISC,CLOSE_DISC))
        outskull_aslspace_data_close = ndimage.binary_closing(outskull_aslspace_data, structure=disc).astype(np.int16)
        outskull_aslspace_data_close_file=newfile(work_dir,outskull_aslspace_file,suffix=f"close-disc-{CLOSE_DISC}")
        outskull_aslspace_data_close_img = nibabel.Nifti1Image(outskull_aslspace_data_close,outskull_aslspace_img.affine,outskull_aslspace_img.header)
        nibabel.save(outskull_aslspace_data_close_img,outskull_aslspace_data_close_file)
        outskull_aslspace_file = outskull_aslspace_data_close_file
        outskull_aslspace_data = outskull_aslspace_data_close

    out_dims = outskull_aslspace_data.shape
    if PHASESHIFT < 0:
        PHASESHIFT_CALC = out_dims[PHASEAXIS] + PHASESHIFT
        OVSTART=PHASESHIFT_CALC
        OVEND=-1
    else:
        PHASESHIFT_CALC = PHASESHIFT
        OVSTART=0
        OVEND=PHASESHIFT

    outer_skull_shift=newfile(work_dir,outskull_aslspace_file,suffix="shift")
    data_shifted = np.roll(outskull_aslspace_data,PHASESHIFT_CALC,PHASEAXIS)
    if not ALLOWOVERLAP:
        if PHASEAXIS==0:
            data_shifted[OVSTART:OVEND,:,:]=0
        elif PHASEAXIS==1:
            data_shifted[:,OVSTART:OVEND,:]=0
        elif PHASEAXIS==2:
            data_shifted[:,:,OVSTART:OVEND]=0
        else:
            print(f"phase axis {PHASEAXIS} not valid. Allowing overlap of mask")     
    shifted_img = nibabel.Nifti1Image(data_shifted,outskull_aslspace_img.affine,outskull_aslspace_img.header)
    nibabel.save(shifted_img,outer_skull_shift)
    outskull_aslspace_file = outer_skull_shift
    outskull_aslspace_data = data_shifted

    outer_skull_shift_final = newfile(artefact_outputdir,assocfile=f"{subject}_{session}_asl_chemical_shift_artefact.nii.gz")
    shutil.copyfile(outer_skull_shift,outer_skull_shift_final)  


def derive_asl_artefact_v1(asl_acq,labels_dict,command_base,aslfile,aslfile_brain,aslfile_brain_mask,workdir,outputdir,RINGTHRESH=0.15,STRELCLOSE=disc3,PHASESHIFT=12,PHASEAXIS=1,FRAC_INT_THRESH="0.7000000000000002",VERT_GRAD="0"):

    FRAC_INT_THRESH_lookup= getParams(labels_dict,'FRAC_INT_THRESH')
    if FRAC_INT_THRESH_lookup:
        FRAC_INT_THRESH = FRAC_INT_THRESH_lookup

    VERT_GRAD_lookup=getParams(labels_dict,'VERT_GRAD')
    if VERT_GRAD_lookup:
        VERT_GRAD = VERT_GRAD_lookup

    RINGTHRESH_lookup=getParams(labels_dict,'RINGTHRESH')
    if RINGTHRESH_lookup:
        RINGTHRESH = np.float64(RINGTHRESH_lookup)

    STRELCLOSE_lookup=getParams(labels_dict,'STRELCLOSE')
    if STRELCLOSE_lookup and STRELCLOSE_lookup in streldict.keys():
        STRELCLOSE = streldict[STRELCLOSE_lookup]

    PHASESHIFT_lookup = getParams(labels_dict,'PHASESHIFT')
    if PHASESHIFT_lookup:
        if isinstance(PHASESHIFT_lookup,dict):
            if asl_acq in PHASESHIFT_lookup.keys():
                PHASESHIFT=int(PHASESHIFT_lookup[asl_acq])
        else:
            PHASESHIFT = int(PHASESHIFT_lookup)
    if getParams(labels_dict,'PHASEAXIS'):
        PHASEAXIS = int(getParams(labels_dict,'PHASEAXIS'))

    params=f" {aslfile}" \
        f" {aslfile_brain}" \
        " -R" \
        f" -f {FRAC_INT_THRESH}" \
        f" -g {VERT_GRAD}" \
        " -m -s"

    command=f"{command_base} bet"\
        " "+params
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    data1 = nibabel.load(aslfile).get_fdata()
    data1 = data1[:,:,:,0]
    data2img = nibabel.load(aslfile_brain)
    data2 = data2img.get_fdata()
    data3img = nibabel.load(aslfile_brain_mask)
    data3 = data3img.get_fdata()

    diff12 = np.abs(data1-data2)
    diff12_img = nibabel.Nifti1Image(diff12,data2img.affine,data2img.header)
    ring = newfile(workdir,assocfile=aslfile,suffix="ring")
    nibabel.save(diff12_img,ring)

    diff12bw = diff12.copy()
    diff12bw_mask = diff12[:,:,:] > RINGTHRESH*np.max(diff12)
    diff12bw[diff12bw_mask]=1
    diff12bw[~diff12bw_mask]=0
    diff12bw = np.int16(diff12bw)
    diff12bw_shifted = np.roll(diff12bw,PHASESHIFT,PHASEAXIS)
    diff12bw_shifted_img = nibabel.Nifti1Image(diff12bw_shifted,data3img.affine,data3img.header)
    ring_shifted = newfile(workdir,assocfile=aslfile,suffix="ring_shifted")
    nibabel.save(diff12bw_shifted_img,ring_shifted)

    overlap_voxels = diff12bw_shifted + data3
    overlap_voxels_mask = overlap_voxels[:,:,:] == 2
    overlap_voxels[overlap_voxels_mask] = 1
    overlap_voxels[~overlap_voxels_mask] = 0
    overlap_voxels = np.int16(overlap_voxels)
    overlap_img = nibabel.Nifti1Image(overlap_voxels,data3img.affine,data3img.header)
    overlap = newfile(workdir,assocfile=aslfile,suffix="artefact_premorph")
    nibabel.save(overlap_img,overlap)

    overlap_voxels_morpho = ndimage.binary_closing(overlap_voxels, structure=STRELCLOSE).astype(np.int16)

    labels = measure.label(overlap_voxels_morpho)
    props = measure.regionprops(labels)
    largest_prop = max(props, key=lambda prop: prop.area)
    overlap_voxels_morpho_clean=np.zeros(overlap_voxels_morpho.shape)
    overlap_voxels_morpho_clean[tuple(largest_prop.coords.T)] = 1
    overlap_voxels_morpho_clean = np.int16(overlap_voxels_morpho_clean)
    overlap_clean_img = nibabel.Nifti1Image(overlap_voxels_morpho_clean,data3img.affine,data3img.header)
    overlap_clean = newfile(workdir,assocfile=aslfile,suffix="artefact")
    nibabel.save(overlap_clean_img,overlap_clean)

    final_clean = newfile(outputdir,assocfile=overlap_clean)
    shutil.copyfile(overlap_clean,final_clean)


def preproc_proc(labels_dict,bids_dir=""):

    cwd=os.getcwd()
    output_dir = cwd

    work_dir=os.path.join(output_dir,"preproc_workdir")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    labels_dict = updateParams(labels_dict,"CWD",cwd)

    command_base, container = getContainer(labels_dict,nodename="preproc", SPECIFIC="FSL_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the fsl version:")
    command = f"{command_base} fslversion"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    # set up dwi to process just the specific dwi session
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    subject = f"sub-{participant_label}"
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')
    session = f"ses-{participant_session}"
    preproc_version = getParams(labels_dict,'PREPROC_VERSION')
    if preproc_version:
        VERSION_TO_RUN = preproc_version
    else:
        VERSION_TO_RUN = "2"

    # calculate asl artefact for acq-prod
    layout = BIDSLayout(bids_dir)
    asl=layout.get(subject=participant_label,session=participant_session,suffix='asl', extension='nii.gz')

    if len(asl) > 0:
        asl_bidsfile=asl[0]
        asl_entities = asl_bidsfile.get_entities()
        if "acquisition" in asl_entities.keys():
            asl_acq = "acq-" + asl_entities["acquisition"]
        else:
            asl_acq = get_bidstag("acq",asl_bidsfile.filename)

        if not asl_acq:
            asl_acq = "default"

        artefact_outputdir = getParams(labels_dict,'DERIVATIVES_DIR')
        if not artefact_outputdir:
            artefact_outputdir = os.path.join(output_dir,"asl_artefact", subject,session)
        else:
            artefact_outputdir = os.path.join(artefact_outputdir,"asl_artefact", subject,session)

        if not os.path.exists(artefact_outputdir):
            os.makedirs(artefact_outputdir, exist_ok=True)

        if VERSION_TO_RUN == "2":
            derive_asl_artefact_v2(asl_acq,labels_dict,command_base, participant_label,participant_session,artefact_outputdir)
        else:
            m0_entities = asl_entities.copy()
            m0_entities["suffix"]="m0scan"
            m0  = layout.get(return_type='file', invalid_filters='allow', **m0_entities)
            if len(m0) > 0:
                m0_file=m0[0]
                m0_file_brain = newfile(work_dir,assocfile=m0_file,suffix="brain")
                m0_file_brain_mask = newfile(work_dir,assocfile=m0_file_brain,suffix="mask")
                derive_asl_artefact_v1(asl_acq,labels_dict, command_base, m0_file,m0_file_brain,m0_file_brain_mask,work_dir,artefact_outputdir)

    return {
        "output_dir":output_dir
    }



class preprocInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class preprocOutputSpec(TraitedSpec):
    output_dir = traits.String(desc="QSIPREP output directory")
    
    
class preproc_pan(BaseInterface):
    input_spec = preprocInputSpec
    output_spec = preprocOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = preproc_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='preproc_node',bids_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(preproc_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


