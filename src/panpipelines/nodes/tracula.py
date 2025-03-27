from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
from panpipelines.utils import transformer as tran
import os
import glob
from bids import BIDSLayout
import shlex
import subprocess
from nipype import logging as nlogging
from shutil import copy
import nibabel as nib
import numpy as np
from nilearn.image import resample_to_img

IFLOGGER=nlogging.getLogger('nipype.interface')

def tracula_proc(labels_dict,bids_dir="",tracula_dir=""):

    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    params= getParams(labels_dict,"TRACULA_PARAMS")

    layout = BIDSLayout(bids_dir)

    subject="sub-"+participant_label
    session="ses-"+session_label
    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    subjects_dir = getParams(labels_dict,'SUBJECTS_DIR')
    os.environ["SUBJECTS_DIR"]=subjects_dir

    command_base, container = getContainer(labels_dict,nodename="tracula", SPECIFIC="TRACULA_CONTAINER",LOGGER=IFLOGGER) 
    command_base = substitute_labels(command_base, labels_dict)

    container_subjects_dir = translate_binding(command_base,subjects_dir)
    os.environ["SINGULARITYENV_SUBJECTS_DIR"]=container_subjects_dir
    
    if not tracula_dir:
        if getParams(labels_dict,'TRACULA_DIR'):
            tracula_dir = getParams(labels_dict,'TRACULA_DIR')
        else:
            tracula_dir = os.path.join(cwd,'tracula_dir')
    if not os.path.isdir(tracula_dir):
        os.makedirs(tracula_dir,exist_ok=True)
    container_tracula_dir=translate_binding(command_base,tracula_dir)
    tracula_config = os.path.join(tracula_dir,f"dmrirc_{subject}_{session}")

    dtroot=os.path.join(tracula_dir,"dtroot")
    if not os.path.isdir(dtroot):
        os.makedirs(dtroot,exist_ok=True)

    dcmroot=os.path.join(tracula_dir,"dcmroot")
    if not os.path.isdir(dcmroot):
        os.makedirs(dcmroot,exist_ok=True)

    workdir=os.path.join(tracula_dir,"workdir")
    if not os.path.isdir(workdir):
        os.makedirs(workdir,exist_ok=True)


    if not os.path.exists(tracula_config) or params == "-prep":
        dwi_entity={}
        dwi_entity["suffix"]="dwi"
        dwi_entity["subject"]=participant_label
        dwi_entity["extension"]='nii.gz'
        if session_label:
            dwi_entity["session"]=session_label
        dwi = layout.get(invalid_filters='allow', **dwi_entity)

        if dwi:
            dwipath=dwi[0].path
            dwibase=os.path.basename(dwipath)
            bvecpath= layout.get_bvec(dwipath)
            bvecbase=os.path.basename(bvecpath)
            bvalpath= layout.get_bval(dwipath)
            bvalbase=os.path.basename(bvalpath)
            dwimeta=dwi[0].get_metadata()
            echospacing = dwimeta["EffectiveEchoSpacing"]
            epifactor = dwimeta["EchoTrainLength"]

            copy(dwipath,os.path.join(dcmroot,dwibase))
            copy(bvecpath,os.path.join(dcmroot,bvecbase))

            with open(bvalpath,"r") as infile:
                bvals=infile.read()
            bvals='\n'.join(bvals.split())
            with open(os.path.join(dcmroot,bvalbase),"w") as outfile:
                outfile.write(bvals)

            dwirpe = [x for x in dwi[0].get_associations() if "dir" in x.path]
            if dwirpe:
                dwirpepath=dwirpe[0].path
                dwirpebase = os.path.basename(dwirpepath)
                copy(dwirpepath,os.path.join(dcmroot,dwirpebase))

                bvecrpebase=os.path.basename(newfile(outputdir=dcmroot,assocfile=dwirpepath,extension="bvec"))
                rpeshape = nib.load(dwirpepath).shape
                dimt=1
                if len(rpeshape) > 3:
                    dimt=rpeshape[3]
                bvecs = np.zeros((3, dimt)) 
                np.savetxt(os.path.join(dcmroot,bvecrpebase), bvecs, fmt="%.3f", delimiter=" ")

                bvalrpebase=os.path.basename(newfile(outputdir=dcmroot,assocfile=dwirpepath,extension="bval"))
                bvals = np.zeros((dimt, 1)) 
                np.savetxt(os.path.join(dcmroot,bvalrpebase), bvals, fmt="%.0f", delimiter=" ")

            else:
                IFLOGGER.error(f"Cannot find DWIRPE for subject. Cannot proceed")
                sys.exit(1)
        else:
            IFLOGGER.error(f"Cannot find DWI for subject. Cannot proceed")
            sys.exit(1)

        config_lines=f"setenv SUBJECTS_DIR {container_subjects_dir}\n" \
                    f"set dtroot = ({container_tracula_dir}/dtroot)\n"\
                    f"set subjlist = ({subject} {subject})\n"\
                    f"set dcmroot = ({container_tracula_dir}/dcmroot)\n"\
                    f"set dcmlist = ({dwibase} {dwirpebase})\n"\
                    f"set bveclist = ({bvecbase} {bvecrpebase})\n"\
                    f"set bvallist = ({bvalbase} {bvalrpebase})\n"\
                    f"set dob0 = 2\n"\
                    f"set pedir = (AP PA)\n"\
                    f"set echospacing = {echospacing*1000}\n"\
                    f"set epifactor = {epifactor}\n"\
                    f"set doeddy = 2 "
                        
        with open(tracula_config,"w") as outfile:
                outfile.write(config_lines)
           
  
    FREEVER="Unknown"
    IFLOGGER.info("Checking the recon-all version:")
    command = f"{command_base} recon-all --version"
    evaluated_command=substitute_labels(command, labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)
    if "-7.3.2-" in results:
        FREEVER="7.3.2"

    if container:
        IFLOGGER.info("\nChecking the container version:")
        command = f"{container} --version"
        evaluated_command=substitute_labels(command, labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

    if not params == "regacpc":
        command=f"{command_base} {params} -c {tracula_config}"
        evaluated_command=substitute_labels(command,labels_dict)
        results = runCommand(evaluated_command,IFLOGGER)

    if params == "-path" or params == "regacpc":

        command_base, container = getContainer(labels_dict,nodename="regacpc_tracula", SPECIFIC="PAN_CONTAINER",LOGGER=IFLOGGER) 
        command_base = substitute_labels(command_base, labels_dict)

        THRESH = getParams(labels_dict,"TRACULA_THRESH")
        if not THRESH:
            THRESH="20"
        dmri_dir= os.path.join(dtroot,subject,"dmri")
        bvec=os.path.join(dmri_dir,"bvecs")
        bval=os.path.join(dmri_dir,"bvals")
        dwipreproc=os.path.join(dmri_dir,"data.nii.gz")

        b0=newfile(outputdir=workdir,assocfile="b0.nii.gz")
        command=f"{command_base} dwiextract -fslgrad {bvec} {bval} {dwipreproc} -bzero {b0}"
        results = runCommand(command)

        meanb0=newfile(outputdir=workdir,assocfile="meanb0.nii.gz")
        command=f"{command_base} fslmaths {b0} -Tmean {meanb0}"
        results = runCommand(command)

        qsiprep_in=getParams(labels_dict,"QSIPREP_OUTPUT_DIR")
        t1acpc=os.path.join(qsiprep_in,subject,"anat",f"{subject}_desc-preproc_T1w.nii.gz")
        dwiref=os.path.join(qsiprep_in,subject,session,"dwi",f"{subject}_{session}_space-T1w_dwiref.nii.gz")
        t1acpc_mask=os.path.join(qsiprep_in,subject,"anat",f"{subject}_desc-brain_mask.nii.gz")
        t1acpc_brain=os.path.join(workdir,f"{subject}_desc-brain.nii.gz")

        command=f"{command_base} fslmaths {t1acpc} -mas {t1acpc_mask} {t1acpc_brain}"
        results = runCommand(command)

        # resample t1acpc to dwi space
        dwiref_img=nib.load(dwiref)

        t1acpc_img=nib.load(t1acpc)
        t1acpc_dwispace = newfile(outputdir=workdir,assocfile=t1acpc,suffix="space-dwi")
        t1acpc_dwispace_img = resample_to_img(t1acpc_img,dwiref_img)
        nib.save(t1acpc_dwispace_img, t1acpc_dwispace)

        t1acpc_brain_img=nib.load(t1acpc_brain)
        t1acpc_brain_dwispace = newfile(outputdir=workdir,assocfile=t1acpc_brain,suffix="space-dwi")
        t1acpc_brain_dwispace_img = resample_to_img(t1acpc_brain_img,dwiref_img,interpolation='nearest')
        nib.save(t1acpc_brain_dwispace_img, t1acpc_brain_dwispace)

        epi_t1acpc=newfile(outputdir=workdir,assocfile="epi_t1acpc")
        epi_t1acpc_mat=newfile(outputdir=workdir,assocfile=epi_t1acpc,extension="mat")
        command=f"{command_base} epi_reg --epi={meanb0} --t1={t1acpc_dwispace} --t1brain={t1acpc_brain_dwispace} --out={epi_t1acpc}"
        results = runCommand(command)

        dpath = os.path.join(dtroot,subject,"dpath")
        tract_acpc_dir = os.path.join(os.path.dirname(dpath),"dpath_acpc")
        os.makedirs(tract_acpc_dir,exist_ok=True)
        for tractdir in os.listdir(dpath):
            tract = os.path.join(dpath,tractdir,"path.pd.nii.gz")
            tract_acpc = newfile(outputdir=tract_acpc_dir,assocfile=tract,prefix=tractdir,intwix="space-acpc")
            tran.applyAffine_flirt(tract, dwiref, tract_acpc, epi_t1acpc_mat, command_base, interp="nearestneighbour")
            tract_acpc_thresh = newfile(outputdir=tract_acpc_dir,assocfile=tract_acpc,suffix=f"desc-thresh{THRESH}") 
            command=f"{command_base} fslmaths {tract} -thrp {THRESH} -bin {tract_acpc_thresh}"
            results = runCommand(command)
            tran.applyAffine_flirt(tract_acpc_thresh, dwiref, tract_acpc_thresh, epi_t1acpc_mat, command_base, interp="nearestneighbour")


    out_files=[]
    out_files.append(tracula_config)

    return {
        "out_files":out_files
    }



class traculaInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)
    tracula_dir = traits.String("",desc="Tracula Output Directory", usedefault=True)

class traculaOutputSpec(TraitedSpec):
    out_files = traits.List(desc='list of files')
    
class tracula_pan(BaseInterface):
    input_spec = traculaInputSpec
    output_spec = traculaOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = tracula_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='tracula_node',bids_dir="",tracula_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(tracula_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


