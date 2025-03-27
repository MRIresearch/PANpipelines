from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import panpipelines.utils.transformer as tr
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def tractseg_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    ALIGN_APPROACH=getParams(labels_dict,"TRACTSEG_ALIGN_APPROACH")
    if not ALIGN_APPROACH:
        ALIGN_APPROACH="FA"

    TRACTSEG_HOME=getParams(labels_dict,"TRACTSEG_HOME")
    if not TRACTSEG_HOME:
        TRACTSEG_HOME=os.path.join(cwd,"tractseg_home")
        os.makedirs(TRACTSEG_HOME,exist_ok=True)  
        labels_dict = updateParams(labels_dict,"TRACTSEG_HOME",TRACTSEG_HOME) 

    # set up initial vars

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')

    input_dir =substitute_labels(input_dir,labels_dict)
    output_dir =substitute_labels("<CWD>/tractseg_out", labels_dict)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    work_dir = substitute_labels("<CWD>/tractseg_work", labels_dict)
    if not os.path.exists(work_dir):
        os.makedirs(work_dir,exist_ok=True)

    prep_dir = substitute_labels("<CWD>/tractseg_prep", labels_dict)
    if not os.path.exists(prep_dir):
        os.makedirs(prep_dir,exist_ok=True)

    # mrtrix container - check version
    mr_command_base,mr_container = getContainer(labels_dict,nodename="tensor", SPECIFIC="MRTRIX_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the mrtrix version:")
    command = f"{mr_command_base} mrconvert --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    if mr_container:
        IFLOGGER.info("\nChecking the container version:")
        command = f"{mr_command_base} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)
    
    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["APPTAINER_TEMPLATEFLOW_HOME"]=translate_binding(mr_command_base,TEMPLATEFLOW_HOME)

    # get qsiprep outputs and transforms - prepare data for TractSeg
    resolution="1"
    struct_mni2009 = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'anat','*_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5'))
    mni2009_mni = tr.get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",suffix="xfm",extension=[".h5"])

    fslmni=os.path.join(f"/opt/fsl/data/standard/MNI152_T1_{resolution}mm.nii.gz")
    fslFAmni=os.path.join(f"/opt/fsl/data/standard/FMRIB58_FA_{resolution}mm.nii.gz")
    mni152=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",resolution=int(resolution),suffix="T1w",extension=[".nii.gz"])
    mni2009=get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=int(resolution),suffix="T1w",extension=[".nii.gz"])
    t1acpc = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'anat','*_desc-preproc_T1w.nii.gz'))
    mask = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(participant_session),'dwi','*_desc-brain_mask.nii.gz'))
    dwiacpc = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(participant_session),'dwi','*_desc-preproc_dwi.nii.gz'))
    dwigrad = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(participant_session),'dwi','*_desc-preproc_dwi.b'))
    dwitrix=newfile(outputdir=prep_dir,assocfile=dwiacpc,extension=".mif")

    IFLOGGER.info("Convert qsiprep dwi to mrtrix format.")
    command=f"{mr_command_base} mrconvert {dwiacpc} {dwitrix} -grad {dwigrad}"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    if ALIGN_APPROACH == "FA":
        IFLOGGER.info("Create Affine transforms from FA.")

        # convert dwitrix to LAS - flirt really needs data in standard orientation to work
        dwitrix_las=newfile(assocfile=dwitrix,intwix="ori-LAS")
        command=f"{mr_command_base} mrconvert {dwitrix} {dwitrix_las} -strides -1,+2,+3,+4"
        runCommand(command)

        tensor_mrtrix = os.path.join(prep_dir,'sub-{}_tensor.mif'.format(participant_label))
        command=f"{mr_command_base} dwi2tensor -mask {mask} {dwitrix_las} {tensor_mrtrix}"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

        fa_mrtrix = newfile(assocfile=dwitrix_las,suffix="fa")
        command=f"{mr_command_base} tensor2metric -mask {mask} -fa {fa_mrtrix} {tensor_mrtrix}"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

        fa_fsl = newfile(assocfile=fa_mrtrix,extension=".nii.gz")
        command=f"{mr_command_base} mrconvert {fa_mrtrix} {fa_fsl}"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

        fa_fsl_mni=newfile(outputdir=prep_dir,assocfile=fa_fsl,intwix="space-MNI152NLin6Asym")
        trans_affine_fsl=os.path.join(prep_dir,f"{participant_label}_dwiacpc_MNI152_fsl.mat")
        tr.fsl_reg_flirt(fa_fsl,fslFAmni,fa_fsl_mni,trans_affine_fsl,mr_command_base,dof="6",cost="mutualinfo")

        inverse_trans_affine_fsl=newfile(outputdir=prep_dir,assocfile=trans_affine_fsl,suffix="inverse")
        tr.invertAffine_FLIRT(trans_affine_fsl, inverse_trans_affine_fsl, mr_command_base)

        trans_affine=newfile(outputdir=prep_dir,assocfile=trans_affine_fsl,suffix="mrtrix")
        command=f"{mr_command_base} transformconvert {trans_affine_fsl} {dwitrix_las} {fslFAmni} flirt_import {trans_affine}"
        runCommand(command)

        dwimni152_las=newfile(outputdir=prep_dir,assocfile=dwitrix_las,intwix="space-MNI152NLin6Asym")
        command=f"{mr_command_base} mrtransform -template {fslFAmni} -strides {fslFAmni} -linear {trans_affine}  {dwitrix_las} {dwimni152_las}"
        runCommand(command)

        dwimni152_las_nii=newfile(assocfile=dwimni152_las,extension=".nii.gz")
        command=f"{mr_command_base} mrconvert {dwimni152_las} {dwimni152_las_nii}"
        runCommand(command)

        gradmni152=newfile(assocfile=dwimni152_las_nii,extension=".b")
        bval=newfile(assocfile=dwimni152_las_nii,extension=".bval")
        bvec=newfile(assocfile=dwimni152_las_nii,extension=".bvec")
        command=f"{mr_command_base} dwigradcheck {dwimni152_las} -export_grad_mrtrix {gradmni152}"
        runCommand(command)
        command=f"{mr_command_base} dwigradcheck {dwimni152_las} -export_grad_fsl {bvec} {bval}"
        runCommand(command)

    else:
        IFLOGGER.info("Create Affine transforms from existing qsiprep transforms.")
        os.chdir(prep_dir)
        t1 = tr.disassembleTransforms(struct_mni2009,"t1",mr_command_base)
        t1mat=[x for x in t1 if x.endswith(".mat")][0]
        IFLOGGER.info(f"Created Affine transforms {t1mat}.")

        t2=tr.disassembleTransforms(mni2009_mni,"t2",mr_command_base)
        t2mat=[x for x in t2 if x.endswith(".mat")][0] 
        IFLOGGER.info(f"Created Affine transforms {t2mat}.")
        os.chdir(cwd)

        t1_fsl=newfile(outputdir=prep_dir,assocfile=t1mat,suffix="fsl")
        tr.convert_affine_ants_to_fsl(t1mat,dwiacpc,mni2009,t1_fsl)

        t2_fsl=newfile(outputdir=prep_dir,assocfile=t2mat,suffix="fsl")
        tr.convert_affine_ants_to_fsl(t2mat,mni2009,mni152,t2_fsl)

        trans_affine_fsl=os.path.join(prep_dir,f"{participant_label}_dwiacpc_MNI152_fsl.mat")
        tr.concatAffine_FLIRT(t1_fsl,t2_fsl, trans_affine_fsl, mr_command_base)

        inverse_trans_affine_fsl=newfile(outputdir=prep_dir,assocfile=trans_affine_fsl,suffix="inverse")
        tr.invertAffine_FLIRT(trans_affine_fsl, inverse_trans_affine_fsl, mr_command_base)

        trans_affine=newfile(outputdir=prep_dir,assocfile=trans_affine_fsl,suffix="mrtrix")
        command=f"{mr_command_base} transformconvert {trans_affine_fsl} {dwiacpc} {mni152} flirt_import {trans_affine}"
        runCommand(command)

        dwimni152=newfile(outputdir=prep_dir,assocfile=dwitrix,intwix="space-MNI152NLin6Asym")
        command=f"{mr_command_base} mrtransform -force -template {mni152} -linear {trans_affine}  {dwitrix} {dwimni152}"
        runCommand(command)

        dwimni152_las=newfile(assocfile=dwimni152,intwix="ori-LAS")
        command=f"{mr_command_base} mrconvert {dwimni152} {dwimni152_las} -strides -1,+2,+3,+4"
        runCommand(command)

        dwimni152_las_nii=newfile(assocfile=dwimni152_las,extension=".nii.gz")
        command=f"{mr_command_base} mrconvert {dwimni152_las} {dwimni152_las_nii}"
        runCommand(command)

        gradmni152=newfile(assocfile=dwimni152_las_nii,extension=".b")
        bval=newfile(assocfile=dwimni152_las_nii,extension=".bval")
        bvec=newfile(assocfile=dwimni152_las_nii,extension=".bvec")
        command=f"{mr_command_base} dwigradcheck {dwimni152_las} -export_grad_mrtrix {gradmni152}"
        runCommand(command)
        command=f"{mr_command_base} dwigradcheck {dwimni152_las} -export_grad_fsl {bvec} {bval}"
        runCommand(command)

    # Run tractseg
    command_base, container = getContainer(labels_dict,nodename="tractseg", SPECIFIC="TRACTSEG_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the tractseg version:")
    command = f"{command_base} TractSeg --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["APPTAINER_TEMPLATEFLOW_HOME"]=translate_binding(command_base,TEMPLATEFLOW_HOME)

    EXTRA_PARAMS = getParams(labels_dict,"EXTRA_TRACTSEG_PARAMS")
    if not EXTRA_PARAMS:
        EXTRA_PARAMS=""

    # generate tensors using mrtrix, use grad from qsiprep
    params="-i "+dwimni152_las_nii+\
        " -o "+output_dir+\
        " --bvals "+bval+\
        " --bvecs "+bvec+\
        " --raw_diffusion_input"

    command=f"{command_base} TractSeg"\
            " "+params + " " + EXTRA_PARAMS

    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    bundles=glob.glob(os.path.join(output_dir,"bundle_segmentations","*.nii.gz"))
    bundles_native_bin_dir=os.path.join(output_dir,"bundles_segmentations_native_bin")
    if not os.path.exists(bundles_native_bin_dir):
        os.makedirs(bundles_native_bin_dir,exist_ok=True)
    
    STORE_PROBS = False
    if "get_probabilities" in command:
        STORE_PROBS = True

    if STORE_PROBS:
        bundles_native_prob_dir=os.path.join(output_dir,"bundles_segmentations_native_prob")
        if not os.path.exists(bundles_native_prob_dir):
            os.makedirs(bundles_native_prob_dir,exist_ok=True)

    TRACTSEG_PROBTHRESH=getParams(labels_dict,"TRACTSEG_PROBTHRESH")
    if not TRACTSEG_PROBTHRESH:
        TRACTSEG_PROBTHRESH="0.5"

    for bundle in bundles:
        if STORE_PROBS:
            bundle_native=newfile(outputdir=bundles_native_prob_dir,assocfile=bundle)
            if ALIGN_APPROACH == "FA":        
                applyAffine_flirt(bundle,fa_fsl,bundle_native,inverse_trans_affine_fsl,mr_command_base,interp="trilinear")
            else:
                applyAffine_flirt(bundle,dwiacpc,bundle_native,inverse_trans_affine_fsl,mr_command_base,interp="trilinear")
            command=f"{mr_command_base} mrconvert -force {bundle_native} {bundle_native} -strides -1,-2,+3"
            runCommand(command)

            bundle_native_bin=newfile(outputdir=bundles_native_bin_dir,assocfile=bundle)
            command=f"{mr_command_base} fslmaths {bundle_native} -thr {TRACTSEG_PROBTHRESH} -bin {bundle_native_bin}"
            runCommand(command)
        else:
            bundle_native_bin=newfile(outputdir=bundles_native_bin_dir,assocfile=bundle)
            if ALIGN_APPROACH == "FA":        
                applyAffine_flirt(bundle,fa_fsl,bundle_native_bin,inverse_trans_affine_fsl,mr_command_base,interp="nearestneighbour")
            else:
                applyAffine_flirt(bundle,dwiacpc,bundle_native_bin,inverse_trans_affine_fsl,mr_command_base,interp="nearestneighbour")

            command=f"{mr_command_base} mrconvert -force {bundle_native_bin} {bundle_native_bin} -strides -1,-2,+3"
            runCommand(command)

    out_files=[]
    out_files.insert(0,inverse_trans_affine_fsl)
    out_files.insert(1,dwiacpc)
    out_files.insert(2,dwimni152_las_nii)

    return {
        "output_dir":cwd,
        "out_files":out_files
    }



class tractsegInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="QSIPREP Output Directory", usedefault=True)

class tractsegOutputSpec(TraitedSpec):
    output_dir = traits.String(desc="Tractseg output directory")
    out_files = traits.List(desc='list of files')
    
class tractseg_pan(BaseInterface):
    input_spec = tractsegInputSpec
    output_spec = tractsegOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = tractseg_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="tractseg_node",input_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(tractseg_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None:
        input_dir = ""
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


