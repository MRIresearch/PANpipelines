from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def mni3dglm_proc(labels_dict,file_template,mask_template,design_file,contrast_file,ftest_file):

    cwd=os.getcwd()
    output_dir=cwd
    # retrieve subject list
    fsldesign_text = getParams(labels_dict,"TEXT_FSL_DESIGN")
    df = pd.read_table(fsldesign_text,sep=",",header=None)

    groupmaskdata=None
    for subindex in range(len(df)):
        participant_label=df[0][subindex].split('sub-')[1]
        labels_dict = updateParams(labels_dict,'PARTICIPANT_LABEL',participant_label)
        subject_mask=substitute_labels(getParams(labels_dict,"STAT_MASK_TEMPLATE"),labels_dict)

        img = nib.load(subject_mask)
        img_dtype = img.header.get_data_dtype()
        data=img.get_fdata()
        if subindex == 0:
            groupmaskdata = data.copy()
        else:
            groupmaskdata = groupmaskdata + data

    if groupmaskdata is not None:
        group_mask_dir = os.path.join(cwd,'group_mask')
        if not os.path.isdir(group_mask_dir):
            os.makedirs(group_mask_dir)
        group_mask = os.path.join(group_mask_dir,'group_mask_mni.nii.gz')
        groupmaskdata[groupmaskdata > 0] = 1
        save_image_to_disk(subject_mask,groupmaskdata,group_mask)


        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslreorient2std"\
            " "+group_mask+ " "+group_mask

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)


        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
            " "+group_mask+ " -bin "+group_mask

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmaths"\
            " "+group_mask+ " -dilM -fillh "+group_mask

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    statsimagestring=''
    stats_image=None
    for subindex in range(len(df)):
        participant_label=df[0][subindex].split('sub-')[1]
        labels_dict = updateParams(labels_dict,'PARTICIPANT_LABEL',participant_label)
        subject_file=getGlob(substitute_labels(getParams(labels_dict,"STAT_FILE_TEMPLATE"),labels_dict))
        statsimagestring= statsimagestring + " " + subject_file 

    if not statsimagestring == "":
        stats_image_dir = os.path.join(cwd,'stats_image')
        if not os.path.isdir(stats_image_dir):
            os.makedirs(stats_image_dir)
        stats_image = os.path.join(stats_image_dir,'stats_image_mni.nii.gz')

        params="-t" \
            " "+ stats_image + \
            " " + statsimagestring 

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> fslmerge"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    
    # permutation
    everythingThere=True

    if everythingThere:
        stats_output_dir = os.path.join(cwd,'stats_results')
        if not os.path.isdir(stats_output_dir):
            os.makedirs(stats_output_dir)

        PERMS="50"
        params = " -i "+stats_image+ \
            " -o "+stats_output_dir+"/out"\
            " -m "+group_mask+\
            " -d "+design_file+\
            " -t "+contrast_file+\
            " -f "+ftest_file+\
            " -n "+PERMS+\
            " -T"

        command="singularity run --cleanenv --no-home <NEURO_CONTAINER> randomise_parallel"\
            " "+params

        evaluated_command=substitute_labels(command, labels_dict)
        IFLOGGER.info(evaluated_command)
        evaluated_command_args = shlex.split(evaluated_command)
        results = subprocess.run(evaluated_command_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT, text=True)
        IFLOGGER.info(results.stdout)

    out_files=[]
    out_files.insert(0,group_mask)
    out_files.insert(1,stats_image)

    return {
        "group_mask":group_mask,
        "stats_image":stats_image,
        "stats_output_dir":stats_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class mni3dglmInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    file_template = traits.String("",desc="file template", usedefault=True)
    mask_template = traits.String("",desc="mask template", usedefault=True)
    design_file = File(desc='Design File')
    contrast_file = File(desc='Contrast File')
    ftest_file = File(desc='Ftest file')

class mni3dglmOutputSpec(TraitedSpec):
    group_mask = File(desc='Group Mask')
    stats_image = File(desc='4D stats image')
    stats_output_dir = traits.String(desc='stats_output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class mni3dglm_pan(BaseInterface):
    input_spec = mni3dglmInputSpec
    output_spec = mni3dglmOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = mni3dglm_proc(
            self.inputs.labels_dict,
            self.inputs.file_template,
            self.inputs.mask_template,
            self.inputs.design_file,
            self.inputs.contrast_file,
            self.inputs.ftest_file
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="mni3dglm_node",file_template="",mask_template="",design_file="",contrast_file="",ftest_file="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(mni3dglm_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
    
    # Specify node inputs
    panpipe_labels = process_fsl_glm(labels_dict)
    pan_node.inputs.labels_dict = labels_dict

    if file_template is None or file_template == "":
        file_template = getParams(labels_dict,"STAT_FILE_TEMPLATE")

    if mask_template is None or mask_template == "":
        mask_template  = getParams(labels_dict,"STAT_MASK_TEMPLATE")

    if design_file is None or design_file == "" or not os.path.isfile(design_file):
        design_file  = getParams(labels_dict,"FSL_DESIGN")

    if contrast_file is None or contrast_file == "" or not os.path.isfile(contrast_file):
        contrast_file = getParams(labels_dict,"FSL_CONTRAST")

    if ftest_file is None or ftest_file == "" or not os.path.isfile(ftest_file):
        ftest_file = getParams(labels_dict,"FSL_FTEST")


    pan_node.inputs.file_template =  file_template
    pan_node.inputs.mask_template =  mask_template
    pan_node.inputs.design_file =  design_file
    pan_node.inputs.contrast_file =  contrast_file
    pan_node.inputs.ftest_file =  ftest_file

    return pan_node


