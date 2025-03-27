from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
from panpipelines.utils import transformer as tran
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging
from shutil import copy

IFLOGGER=nlogging.getLogger('nipype.interface')

def xtract_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')


    output_dir = os.path.join(cwd,'xtract_results')
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    xtractout_dir = os.path.join(output_dir,'xtract_out')
    if not os.path.isdir(xtractout_dir):
        os.makedirs(xtractout_dir,exist_ok=True)

    dmri_dir = os.path.join(output_dir,'qsidmri')
    if not os.path.isdir(dmri_dir):
        os.makedirs(dmri_dir,exist_ok=True)

    transforms_dir = os.path.join(output_dir,'transforms')
    if not os.path.isdir(transforms_dir):
        os.makedirs(transforms_dir,exist_ok=True)

    work_dir = os.path.join(cwd,'xtract_workdir')
    if not os.path.isdir(work_dir):
        os.makedirs(work_dir,exist_ok=True)

    input_dir=substitute_labels(input_dir,labels_dict)
    dwi = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(session_label),'dwi','*_desc-preproc_dwi.nii.gz'))
    dwiref = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(session_label),'dwi','*_dwiref.nii.gz'))
    mask = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(session_label),'dwi','*_desc-brain_mask.nii.gz'))
    grad = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(session_label),'dwi','*_desc-preproc_dwi.b'))

    mr_command_base, mr_container = getContainer(labels_dict,nodename="xtract", SPECIFIC="MRTRIX_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the mrtrix version:")
    command = f"{mr_command_base} mrinfo --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    if mr_container:
        IFLOGGER.info("\nChecking the container version:")
        command = f"{mr_container} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

    IFLOGGER.info("Preparing data from qsiprep for bedpost run")
    dwitrix = newfile(outputdir=work_dir, assocfile=dwi, extension=".mif")
    command=f"{mr_command_base} mrconvert {dwi} {dwitrix} -grad {grad}"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    bvec=os.path.join(dmri_dir,"bvecs")
    bval=os.path.join(dmri_dir,"bvals")
    command=f"{mr_command_base} dwigradcheck {dwitrix} -export_grad_fsl {bvec} {bval}"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    dwipreproc = os.path.join(dmri_dir,"data.nii.gz")
    command=f"{mr_command_base} mrconvert {dwitrix} {dwipreproc}"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    nodif_brain_mask = os.path.join(dmri_dir,"nodif_brain_mask.nii.gz")
    copy(mask,nodif_brain_mask)

    command_base, container = getContainer(labels_dict,nodename="xtract", SPECIFIC="XTRACT_CONTAINER",LOGGER=IFLOGGER)
    IFLOGGER.info("Checking the fsl version:")
    command = f"{command_base} fslversion"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    if container:
        IFLOGGER.info("\nChecking the container version:")
        command = f"{container} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

    IFLOGGER.info("Run bedpostx_gpu")
    command=f"{command_base} bedpostx_gpu {dmri_dir} -n 3 -model 2"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    IFLOGGER.info("Calculate transforms to MNI152 space")

    TEMPLATEFLOW_HOME=getParams(labels_dict,"TEMPLATEFLOW_HOME")
    if not TEMPLATEFLOW_HOME:
        TEMPLATEFLOW_HOME=os.path.abspath("TemplateFlow")
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    mnilin6_res1_ras = str(tran.get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",resolution=1,suffix="T1w",extension=[".nii.gz"]))
    mnilin6_res1_las= newfile(outputdir=work_dir,assocfile=mnilin6_res1_ras,suffix="ori-LAS")
    tran.reorient(mnilin6_res1_ras,"LAS",mnilin6_res1_las)

    mni2009_res1_ras = str(tran.get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin2009cAsym",resolution=1,suffix="T1w",extension=[".nii.gz"]))
    mni2009_res1_las=newfile(outputdir=work_dir,assocfile=mni2009_res1_ras,suffix="ori-LAS")
    tran.reorient(mni2009_res1_ras,"LAS",mni2009_res1_las)

    mni2009_mnilin6_warp = str(tran.get_template_ref(TEMPLATEFLOW_HOME,"MNI152NLin6Asym",suffix="xfm",extension=[".h5"]))
    t1acpc_mni2009_warp=str(getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'anat','*_from-T1w_to-MNI*')))

    os.chdir(work_dir)
    t1 = tran.disassembleTransforms(t1acpc_mni2009_warp,"t1",command_base)
    t1.sort()
    t2 = tran.disassembleTransforms(mni2009_mnilin6_warp,"t2",command_base)
    t2.sort()
    os.chdir(cwd)

    fulltransform=[]
    fulltransform.append(t1[0])
    fulltransform.append(t1[1])
    fulltransform.append(t2[0])
    fulltransform.append(t2[1])

    dwiacpc_mni152_warp = newfile(outputdir=work_dir,assocfile="dwiacpc_mnilin6_warp",extension="nii.gz")
    tran.apply_transform_ants(dwiref,mnilin6_res1_las,dwiacpc_mni152_warp,fulltransform,command_base,composite=True)

    # use mr_command_base as wb_command_base has issue with --nv gpu access
    diff2std_warp = newfile(outputdir=transforms_dir,assocfile="diff2std_warp",extension="nii.gz")
    tran.convertWarp_toFNIRT(dwiacpc_mni152_warp, diff2std_warp, dwiref, mr_command_base)

    std2diff_warp = newfile(outputdir=transforms_dir,assocfile="std2diff_warp",extension="nii.gz")
    tran.invertWarpfield_FNIRT(dwiref,diff2std_warp,std2diff_warp ,command_base)

    IFLOGGER.info("Run xtract")
    command=f"{command_base} xtract -bpx {dmri_dir}.bedpostX -out {xtractout_dir} -species HUMAN -stdwarp {std2diff_warp} {diff2std_warp} -gpu "
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    THRESH = getParams(labels_dict,"XTRACT_THRESH")
    if not THRESH:
        THRESH="0.001"

    tracts = os.path.join(xtractout_dir,"tracts")
    for tractdir in os.listdir(tracts):
        tract = os.path.join(tracts,tractdir,"densityNorm.nii.gz")
        tract_acpc_dir = os.path.join(os.path.dirname(tracts),"tracts_acpc")
        os.makedirs(tract_acpc_dir,exist_ok=True)
        tract_acpc = newfile(outputdir=tract_acpc_dir,assocfile=tract,prefix=tractdir,suffix="space-acpc")
        tran.applyWarp_fnirt(tract,dwiref,tract_acpc,std2diff_warp,command_base,interp="nn")

        tract_acpc_thresh = newfile(outputdir=tract_acpc_dir,assocfile=tract_acpc,suffix=f"desc-thresh{THRESH}") 
        command=f"{command_base} fslmaths {tract} -thr {THRESH} -bin {tract_acpc_thresh}"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

        tran.applyWarp_fnirt(tract_acpc_thresh,dwiref,tract_acpc_thresh,std2diff_warp,command_base,interp="nn",relative=True)

    out_files=[]

    return {
        "output_dir":output_dir,
        "out_files":out_files
    }



class xtractInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="QSIPREP Output Directory", usedefault=True)

class xtractOutputSpec(TraitedSpec):
    output_dir = traits.String(desc="XTRACT output directory")
    out_files = traits.List(desc='list of files')
    
class xtract_pan(BaseInterface):
    input_spec = xtractInputSpec
    output_spec = xtractOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = xtract_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="xtract_node",input_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(xtract_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None:
        input_dir = ""
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


