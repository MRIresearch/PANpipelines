import nitransforms as nit
import nibabel as nib
import os
import importlib
import tempfile
import glob
from subprocess import check_call
import re
from panpipelines.utils import util_functions
import logging
import sys

LOGGER = logging.getLogger("panpipelines.utils.transformer")
LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s | %(asctime)s | %(levelname)s | %(message)s')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
LOGGER.addHandler(stdout_handler)


def fsleyes_view(NEURO_CONTAINER,params):
    command=f"singularity run {NEURO_CONTAINER} fsleyes"\
            " "+params
    os.system(command)

def get_orientation_from_file(filename,type="default"):
    if type=="ants_transform":
        antstrans=nit.io.itk.ITKLinearTransform.from_filename(filename)
        affine=antstrans.to_ras()
    elif type=="image":
        img = nib.load(filename)
        affine=img.affine
    else:
        affine=filename
    return ["".join(nib.orientations.aff2axcodes(affine)),affine]

def reorient(input_file, ori, out_file=None):
    from nipype.interfaces.image import Reorient
    from nipype import Node

    reorient_node = Node(Reorient(),name="reorient_to_{}".format(ori))
    reorient_node.inputs.in_file =  input_file
    reorient_node.inputs.orientation=ori
    results = reorient_node.run()
    if out_file is not None:
        if os.path.isdir(out_file):
            os.system("cp {} {}".format(results.outputs.out_file,out_file))
            out_file=os.path.join(out_file, os.path.basename(results.outputs.out_file))
        else:
            os.system("cp {} {}".format(results.outputs.out_file,out_file))
    else:
        out_file = results.outputs.out_file
    return out_file

def convert_affine_ants_to_fsl(antstrans_file, moving, reference, fsltrans_file):
    antstrans=nit.io.itk.ITKLinearTransform.from_filename(antstrans_file)
    movimg=nib.load(moving)
    refimg=nib.load(reference)
    fsltr=nit.io.fsl.FSLLinearTransform.from_ras(antstrans.to_ras(),movimg,refimg)
    fsltr.to_filename(fsltrans_file)

def convert_affine_fsl_to_ants(fsltrans_file, moving, reference, antstrans_file):
    fsltrans=nit.io.fsl.FSLLinearTransform.from_filename(fsltrans_file)
    movimg=nib.load(moving)
    refimg=nib.load(reference)
    antstr=nit.io.itk.ITKLinearTransform.from_ras(fsltrans.to_ras(moving,refimg))
    antstr.to_filename(antstrans_file)

def get_template_ref(TEMPLATEFLOW_HOME,template_space,suffix=None,desc=None,resolution=None,extension=[".nii.gz"]):
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
    
    from templateflow import api as tf
    
    template_ref=tf.get(template_space,resolution=resolution,desc=desc,suffix=suffix,extension=extension)
    return template_ref

def apply_transform_mni_to_mni2009_ants_ori(TEMPLATEFLOW_HOME,input_file,out_file, NEURO_CONTAINER,resolution=1,transform_ori="RAS:RAS",target_ori="RAS",reverse=False, costfunction=None,output_type=None):
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    from templateflow import api as tf
    mninlin6_mni2009_trans=tf.get("MNI152NLin2009cAsym",suffix="xfm",extension=[".h5"])
    mni2009_t1_ref=tf.get("MNI152NLin2009cAsym",resolution=resolution,desc=None,suffix="T1w",extension=[".nii.gz"])

    apply_transform_ants_ori(input_file, mni2009_t1_ref,out_file,mninlin6_mni2009_trans,NEURO_CONTAINER,transform_ori="RAS:RAS",target_ori="RAS",reverse=reverse, costfunction=costfunction,output_type=output_type)


def apply_transform_mni_to_mni2009_ants(TEMPLATEFLOW_HOME,input_file,out_file, NEURO_CONTAINER,resolution=1,reverse=False, costfunction=None,output_type=None):
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    from templateflow import api as tf
    mninlin6_mni2009_trans=tf.get("MNI152NLin2009cAsym",suffix="xfm",extension=[".h5"])
    mni2009_t1_ref=tf.get("MNI152NLin2009cAsym",resolution=resolution,desc=None,suffix="T1w",extension=[".nii.gz"])

    apply_transform_ants(input_file, mni2009_t1_ref,out_file,mninlin6_mni2009_trans,NEURO_CONTAINER,reverse=reverse, costfunction=costfunction,output_type=output_type)

def apply_transform_ants_ori(input_file,ref_file, out_file, trans_mat, NEURO_CONTAINER, transform_ori="RAS:RAS",target_ori="RAS", reverse=False, costfunction=None, output_type=None):

    input_file = os.path.abspath(input_file)
    ref_file=os.path.abspath(ref_file)
    out_file=os.path.abspath(out_file)

    expected_mov_ori = transform_ori.split(":")[0]
    expected_ref_ori = transform_ori.split(":")[1]
    
    # Ensure input_file, reference_file and transform are in the same orientation
    ref_ori = get_orientation_from_file(ref_file,"image")
    if not ref_ori[0] == expected_ref_ori:
        print("reorienting  ref_file {} from ref_ori {} to expected_ref_ori {}".format(ref_file, ref_ori, expected_ref_ori))
        ref_file=reorient(ref_file, expected_ref_ori, os.path.dirname(out_file))

    mov_ori = get_orientation_from_file(input_file,"image")
    if not mov_ori[0] == expected_mov_ori:
        print("reorienting input_file (moving) {} from mov_ori {} to expected_mov_ori {}".format(input_file, mov_ori, expected_mov_ori))
        input_file=reorient(input_file, expected_mov_ori, os.path.dirname(out_file))

    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    img = nib.load(input_file)
    dimz=1
    if len(img.header.get_data_shape()) > 3:
        dimz = img.header.get_data_shape()[3]

    image_type = "1"
    if dimz > 1:
        image_type = "3"

    if output_type:
        output_type = f"-u {output_type}"
    else:
        output_type = ""

    TRANSFORMS=""
    if isinstance(trans_mat,list) and isinstance(reverse,list):
        for transcount in range(len(trans_mat)):
            trans_item = os.path.abspath(trans_mat[transcount])
            reverse_item = reverse[transcount]
            if reverse_item:
                TRANSFORMS = " -t [" + str(trans_item) + ",1]" + TRANSFORMS
            else:
                TRANSFORMS = " -t " + str(trans_item)  + TRANSFORMS
    else:
        trans_math = os.path.abspath(trans_mat)
        if reverse:
            TRANSFORMS = " -t [" + str(trans_mat) + ",1]"
        else:
            TRANSFORMS = " -t " + str(trans_mat) 
    # for labels, atlases consider -n NearestNeighbor
    params="-d 3" \
        " -e " + image_type +\
        " -i " + str(input_file) +\
        " -f 0"\
        " --float 1"\
        " -n " + costfunction+\
        " -o " + str(out_file) +\
        " -r " + str(ref_file) + \
        TRANSFORMS + \
        " -v 1"  + \
        " " + output_type

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsApplyTransforms"\
            " "+params

    print(command)
    os.system(command)

    # quick hack to fix issue with templateflow transfomr - 5 dims instead of 3 dims used in header
    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} fslroi"\
            " "+out_file+" "+out_file + " 0 "+str(dimz)
    os.system(command)

    # Transform to target orientation
    # Ensure input_file, reference_file and transform are in the same orientation
    actual_target_ori = get_orientation_from_file(out_file,"image")
    if not actual_target_ori[0] == target_ori:
        print("reorienting  target_file {} from actual_target_ori {} to {}".format(out_file, actual_target_ori, target_ori))
        out_file=reorient(out_file, target_ori,out_file)

    return out_file


def apply_transform_ants(input_file,ref_file, out_file, trans_mat, NEURO_CONTAINER, reverse=False, costfunction=None,output_type=None):

    input_file = os.path.abspath(input_file)
    ref_file=os.path.abspath(ref_file)
    out_file=os.path.abspath(out_file)
    
    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    img = nib.load(input_file)
    dimz=1
    if len(img.header.get_data_shape()) > 3:
        dimz = img.header.get_data_shape()[3]

    image_type = "1"
    if dimz > 1:
        image_type = "3"

    if output_type:
        output_type = f"-u {output_type}"
    else:
        output_type = ""

    TRANSFORMS=""
    if isinstance(trans_mat,list) and isinstance(reverse,list):
        for transcount in range(trans_mat):
            trans_item = os.path.abspath(trans_mat[transcount])
            reverse_item = reverse[transcount]
            if reverse_item:
                TRANSFORMS = " -t [" + str(trans_item) + ",1]" + TRANSFORMS
            else:
                TRANSFORMS = " -t" + str(trans_item)  + TRANSFORMS
    else:
        trans_mat=os.path.abspath(trans_mat)
        if reverse:
            TRANSFORMS = " -t [" + trans_mat + ",1]"
        else:
            TRANSFORMS = " -t " + str(trans_mat) 

    # for labels, atlases consider -n NearestNeighbor
    params="-d 3" \
        " -e " + image_type +\
        " -i " + str(input_file) +\
        " -f 0"\
        " --float 1"\
        " -n " + costfunction+\
        " -o " + str(out_file) +\
        " -r " + str(ref_file) + \
        TRANSFORMS + \
        " -v 1" + \
        " " + output_type

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsApplyTransforms"\
            " "+params

    print(command)
    os.system(command)

    # quick hack to fix issue with templateflow transfomr - 5 dims instead of 3 dims used in header
    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} fslroi"\
            " "+out_file+" "+out_file + " 0 "+str(dimz)
    os.system(command)


def resample_ants_ori(input_file,ref_file, out_file, NEURO_CONTAINER,transform_ori="RAS:RAS",target_ori="RAS", costfunction=None,output_type=None):

    input_file = os.path.abspath(input_file)
    ref_file=os.path.abspath(ref_file)
    out_file=os.path.abspath(out_file)
    
    expected_mov_ori = transform_ori.split(":")[0]
    expected_ref_ori = transform_ori.split(":")[1]
    
    # Ensure input_file, reference_file and transform are in the same orientation
    ref_ori = get_orientation_from_file(ref_file,"image")
    if not ref_ori[0] == expected_ref_ori:
        print("reorienting  ref_file {} from ref_ori {} to expected_ref_ori {}".format(ref_file, ref_ori, expected_ref_ori))
        ref_file=reorient(ref_file, expected_ref_ori, os.path.dirname(out_file))

    mov_ori = get_orientation_from_file(input_file,"image")
    if not mov_ori[0] == expected_mov_ori:
        print("reorienting input_file (moving) {} from mov_ori {} to expected_mov_ori {}".format(input_file, mov_ori, expected_mov_ori))
        input_file=reorient(input_file, expected_mov_ori, os.path.dirname(out_file))

    img = nib.load(input_file)
    dimz=1
    if len(img.header.get_data_shape()) > 3:
        dimz = img.header.get_data_shape()[3]

    image_type = "1"
    if dimz > 1:
        image_type = "3"

    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    if output_type:
        output_type = f"-u {output_type}"
    else:
        output_type = ""

    params="-d 3" \
        " -e " + image_type +\
        " -i " + str(input_file) +\
        " -f 0"\
        " --float 1"\
        " -o " + str(out_file) +\
        " -n " + costfunction+\
        " -r " + str(ref_file) + \
        " -t identity" + \
        " -v 1" + \
        " " + output_type

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsApplyTransforms"\
            " "+params

    os.system(command)
    
def resample_ants(input_file,ref_file, out_file, NEURO_CONTAINER, costfunction=None,output_type=None):

    input_file = os.path.abspath(input_file)
    ref_file=os.path.abspath(ref_file)
    out_file=os.path.abspath(out_file)
    
    img = nib.load(input_file)
    dimz=1
    if len(img.header.get_data_shape()) > 3:
        dimz = img.header.get_data_shape()[3]

    image_type = "1"
    if dimz > 1:
        image_type = "3"

    if costfunction is None:
        costfunction="LanczosWindowedSinc"

    if output_type:
        output_type = f"-u {output_type}"
    else:
        output_type = ""

    params="-d 3" \
        " -e " + image_type +\
        " -i " + str(input_file) +\
        " -f 0"\
        " --float 1"\
        " -o " + str(out_file) +\
        " -n " + costfunction+\
        " -r " + str(ref_file) + \
        " -t identity" + \
        " -v 1" + \
        " " + output_type

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsApplyTransforms"\
            " "+params

    os.system(command)

def ants_registration_ori(moving, reference, transform, NEURO_CONTAINER, transform_ori="RAS:RAS",target_ori="RAS", composite=False):
    
    transform=os.path.abspath(transform)
    reference=os.path.abspath(reference)
    moving=os.path.abspath(moving)
    
    expected_mov_ori = transform_ori.split(":")[0]
    expected_ref_ori = transform_ori.split(":")[1]
    
    # Ensure input_file, reference_file and transform are in the same orientation
    ref_ori = get_orientation_from_file(reference,"image")
    if not ref_ori[0] == expected_ref_ori:
        print("reorienting  ref_file {} from ref_ori {} to expected_ref_ori {}".format(reference, ref_ori, expected_ref_ori))
        reference=reorient(reference, expected_ref_ori, os.path.dirname(transform))

    mov_ori = get_orientation_from_file(moving,"image")
    if not mov_ori[0] == expected_mov_ori:
        print("reorienting input_file (moving) {} from mov_ori {} to expected_mov_ori {}".format(moving, mov_ori, expected_mov_ori))
        moving=reorient(moving, expected_mov_ori, os.path.dirname(transform))
    
    if composite:
        composite_param= " --write-composite-transform 1"
    else:
        composite_param= " --write-composite-transform 0"

    params="--collapse-output-transforms 1" \
    " --dimensionality 3" \
    " --winsorize-image-intensities [ 0.025, 0.975 ]"\
    " --use-histogram-matching 1"\
    f" --initial-moving-transform [ {reference}, {moving}, 1 ] "\
    " --initialize-transforms-per-stage 0" \
    " --interpolation LanczosWindowedSinc" \
    f" --output [ {transform}, {transform}_Warped.nii.gz ]"\
    " --transform Rigid[ 0.1 ] "\
    f" --MI[ {reference}, {moving}, 1, 32, Regular, 0.25 ]"\
    " --convergence [ 1000x500x250x100, 1e-06, 10 ]"\
    " --shrink-factors 8x4x2x1"\
    " --smoothing-sigmas 3x2x1x0vox"\
    " --transform Affine[ 0.1 ] "\
    f" --MI[ {reference}, {moving}, 1, 32, Regular, 0.25 ]"\
    " --convergence [ 1000x500x250x100, 1e-06, 10 ]"\
    " --shrink-factors 8x4x2x1"\
    " --smoothing-sigmas 3x2x1x0vox"\
    " --transform SyN[0.1,3,0] "\
    f" --CC[ {reference}, {moving}, 1,4 ]"\
    " --convergence [ 100x70x50x20, 1e-06, 10 ]"\
    " --shrink-factors 8x4x2x1"\
    " --smoothing-sigmas 3x2x1x0vox"\
    + composite_param

    
    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsRegistration"\
            " "+params

    os.system(command)
    
    transform_dir=os.path.dirname(transform)
    dirs = os.listdir(transform_dir)
    candidates=[s for s in dirs if re.findall(r'.*' +os.path.basename(transform)+ '\d.*',s)]
    forward = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() not in s.upper()]
    inverse = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() in s.upper()]
                             
    forward.sort()

    return {"forward": forward, "inverse" : inverse}
    
    
    
def ants_registration(moving, reference, transform, NEURO_CONTAINER, composite=False):
    
    transform=os.path.abspath(transform)
    reference=os.path.abspath(reference)
    moving=os.path.abspath(moving)
    
    if composite:
        composite_param= " --write-composite-transform 1"
    else:
        composite_param= " --write-composite-transform 0"

    params="--collapse-output-transforms 1" \
    " --dimensionality 3" \
    " --winsorize-image-intensities [ 0.025, 0.975 ]"\
    " --use-histogram-matching 1"\
    f" --initial-moving-transform [ {reference}, {moving}, 1 ] "\
    " --initialize-transforms-per-stage 0" \
    " --interpolation LanczosWindowedSinc" \
    f" --output [ {transform}, {transform}_Warped.nii.gz ]"\
    " --transform Rigid[ 0.1 ] "\
    f" --metric MI[{reference}, {moving}, 1, 32, Regular, 0.25 ]"\
    " --convergence [ 1000x500x250x100, 1e-06, 10 ]"\
    " --shrink-factors 8x4x2x1"\
    " --smoothing-sigmas 3x2x1x0vox"\
    " --transform Affine[ 0.1 ] "\
    f" --metric MI[{reference}, {moving}, 1, 32, Regular, 0.25 ]"\
    " --convergence [ 1000x500x250x100, 1e-06, 10 ]"\
    " --shrink-factors 8x4x2x1"\
    " --smoothing-sigmas 3x2x1x0vox"\
    " --transform SyN[0.1,3,0] "\
    f" --metric CC[{reference}, {moving}, 1,4 ]"\
    " --convergence [ 100x70x50x20, 1e-06, 10 ]"\
    " --shrink-factors 8x4x2x1"\
    " --smoothing-sigmas 3x2x1x0vox"\
    + composite_param

    
    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsRegistration"\
            " "+params

    os.system(command)
    
    transform_dir=os.path.dirname(transform)
    dirs = os.listdir(transform_dir)
    candidates=[s for s in dirs if re.findall(r'.*' +os.path.basename(transform)+ '\d.*',s)]
    forward = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() not in s.upper()]
    inverse = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() in s.upper()]
                             
    forward.sort()

    return {"forward": forward, "inverse" : inverse}
    

# ensure that moving and reference are in RAS before calculating transform
def ants_registration_rigid_ori(moving, reference, transform, NEURO_CONTAINER,transform_ori="RAS:RAS",target_ori="RAS"):
    
    transform=os.path.abspath(transform)
    reference=os.path.abspath(reference)
    moving=os.path.abspath(moving)
       
    expected_mov_ori = transform_ori.split(":")[0]
    expected_ref_ori = transform_ori.split(":")[1]
    
    # Ensure input_file, reference_file and transform are in the same orientation
    ref_ori = get_orientation_from_file(reference,"image")
    if not ref_ori[0] == expected_ref_ori:
        print("reorienting  ref_file {} from ref_ori {} to expected_ref_ori {}".format(reference, ref_ori, expected_ref_ori))
        reference=reorient(reference, expected_ref_ori, os.path.dirname(transform))

    mov_ori = get_orientation_from_file(moving,"image")
    if not mov_ori[0] == expected_mov_ori:
        print("reorienting input_file (moving) {} from mov_ori {} to expected_mov_ori {}".format(moving, mov_ori, expected_mov_ori))
        moving=reorient(moving, expected_mov_ori, os.path.dirname(transform))

    params="--collapse-output-transforms 1" \
    " --dimensionality 3" \
    f" --initial-moving-transform [ {reference}, {moving}, 1 ] "\
    " --initialize-transforms-per-stage 0" \
    " --interpolation LanczosWindowedSinc" \
    f" --output [ {transform}, {transform}_Warped.nii.gz ]"\
    " --transform Rigid[ 0.2 ] "\
    f" --metric Mattes[ {reference}, {moving}, 1, 32, Random, 0.25 ]"\
    " --convergence [ 10000x1000x10000x10000, 1e-06, 10 ]"\
    " --smoothing-sigmas 7.0x3.0x1.0x0.0vox"\
    " --shrink-factors 8x4x2x1"\
    " --use-histogram-matching 1"\
    " --winsorize-image-intensities [ 0.025, 0.975 ]"\
    " --write-composite-transform 0"

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsRegistration"\
            " "+params

    os.system(command)
    
    final_transform=transform+"0GenericAffine.mat"

    return final_transform

def ants_registration_rigid(moving, reference, transform, NEURO_CONTAINER):
    
    transform=os.path.abspath(transform)
    reference=os.path.abspath(reference)
    moving=os.path.abspath(moving)

    params="--collapse-output-transforms 1" \
    " --dimensionality 3" \
    f" --initial-moving-transform [ {reference}, {moving}, 1 ] "\
    " --initialize-transforms-per-stage 0" \
    " --interpolation LanczosWindowedSinc" \
    f" --output [ {transform}, {transform}_Warped.nii.gz ]"\
    " --transform Rigid[ 0.2 ] "\
    f" --metric Mattes[ {reference}, {moving}, 1, 32, Random, 0.25 ]"\
    " --convergence [ 10000x1000x10000x10000, 1e-06, 10 ]"\
    " --smoothing-sigmas 7.0x3.0x1.0x0.0vox"\
    " --shrink-factors 8x4x2x1"\
    " --use-histogram-matching 1"\
    " --winsorize-image-intensities [ 0.025, 0.975 ]"\
    " --write-composite-transform 0"

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsRegistration"\
            " "+params

    os.system(command)
    
    final_transform=transform+"0GenericAffine.mat"

    return final_transform

# ensure that moving and reference are in RAS before calculating transform
def ants_registration_quick_ori(moving, reference, transform, NEURO_CONTAINER,transform_ori="RAS:RAS",target_ori="RAS",threads=8):
    
    transform=os.path.abspath(transform)
    reference=os.path.abspath(reference)
    moving=os.path.abspath(moving)
       
    if threads is not None:
        threadparams=" -n " + str(threads)
        
    expected_mov_ori = transform_ori.split(":")[0]
    expected_ref_ori = transform_ori.split(":")[1]
    
    # Ensure input_file, reference_file and transform are in the same orientation
    ref_ori = get_orientation_from_file(reference,"image")
    if not ref_ori[0] == expected_ref_ori:
        print("reorienting  ref_file {} from ref_ori {} to expected_ref_ori {}".format(reference, ref_ori, expected_ref_ori))
        reference=reorient(reference, expected_ref_ori, os.path.dirname(transform))

    mov_ori = get_orientation_from_file(moving,"image")
    if not mov_ori[0] == expected_mov_ori:
        print("reorienting input_file (moving) {} from mov_ori {} to expected_mov_ori {}".format(moving, mov_ori, expected_mov_ori))
        moving=reorient(moving, expected_mov_ori, os.path.dirname(transform))

    params=f" -f {reference}" \
    f" -m {moving}" \
    f" -o {transform}"\
    + threadparams

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsRegistrationSyNQuick.sh"\
            " "+params

    os.system(command)
    
    transform_dir=os.path.dirname(transform)
    dirs = os.listdir(transform_dir)
    candidates=[s for s in dirs if re.findall(r'.*' +os.path.basename(transform)+ '\d.*',s)]
    forward = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() not in s.upper()]
    inverse = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() in s.upper()]
                             
    forward.sort()

    return {"forward": forward, "inverse" : inverse}

# ensure that moving and reference are in RAS before calculating transform
def ants_registration_quick(moving, reference, transform, NEURO_CONTAINER,threads=8):
    
    transform=os.path.abspath(transform)
    reference=os.path.abspath(reference)
    moving=os.path.abspath(moving)
       
    if threads is not None:
        threadparams=" -n " + str(threads)
        
    params=f" -f {reference}" \
    f" -m {moving}" \
    f" -o {transform}"\
    + threadparams

    command=f"singularity run --cleanenv --no-home {NEURO_CONTAINER} antsRegistrationSyNQuick.sh"\
            " "+params

    os.system(command)
    
    transform_dir=os.path.dirname(transform)
    dirs = os.listdir(transform_dir)
    candidates=[s for s in dirs if re.findall(r'.*' +os.path.basename(transform)+ '\d.*',s)]
    forward = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() not in s.upper()]
    inverse = [os.path.join(transform_dir,s) for s in candidates if "Inverse".upper() in s.upper()]
                             
    forward.sort()

    return {"forward": forward, "inverse" : inverse}


    return candidates


def fsl_reg_flirt(input,reference,out,transmat,neuroimg,dof="12",cost="mutualinfo"):
    cmd=f"singularity run {neuroimg} flirt"\
        f" -in {input}"\
        f" -ref {reference}"\
        f" -out {out}"\
        f" -omat {transmat}"\
        f" -dof {dof}"\
        f" -cost {cost}"
    exit_code = check_call([cmd], shell=True)

def applyAffine_flirt(input,reference,out,transmat,neuroimg,interp="trilinear"):
    cmd=f"singularity run {neuroimg} flirt"\
        f" -in {input}"\
        f" -ref {reference}"\
        f" -out {out}"\
        f" -applyxfm"\
        f" -interp {interp}"\
        f" -init {transmat}"
    exit_code = check_call([cmd], shell=True)

def fsl_reg_fnirt(input,reference,out,transwarp,neuroimg,transmat=None):
    if transmat is not None:
        transmat_param=f" --aff={transmat}"
    else:
        transmat_param=""
    
    cmd=f"singularity run {neuroimg} fnirt"\
        f" --in={input}"\
        f" --ref={reference}"\
        f" --iout={out}"\
        + transmat_param + \
        f" --cout={transwarp}"
    
    exit_code = check_call([cmd], shell=True)
    
def fsl_register_nonlin(input,reference,out,neuroimg):
    trans_str= util_functions.getTransName(input, reference)
    pre_aff = util_functions.newfile(prefix=f"{trans_str}",suffix="affine",extension="mat")
    pre_aff_out = util_functions.newfile(assocfile=pre_aff,suffix="outfile",extension=".nii.gz")
    fsl_reg_flirt(input,reference,pre_aff_out,pre_aff,neuroimg)
    
    fwd_warp = util_functions.newfile(prefix=f"{trans_str}",suffix="warp",extension="nii.gz")
    fwd_warp_out = util_functions.newfile(assocfile=fwd_warp,suffix="outfile",extension=".nii.gz")
    fsl_reg_fnirt(input,reference,fwd_warp_out,fwd_warp,neuroimg,transmat=pre_aff)
    
    inv_warp = util_functions.newfile(prefix=f"{trans_str}",suffix="invwarp",extension="nii.gz")
    invertWarpfield_FNIRT(input, fwd_warp, inv_warp, neuroimg)
    
    return {"forward": fwd_warp, "inverse": inv_warp}

    
def applyWarp_fnirt(input,reference,out,transwarp,neuroimg,interp="trilinear",premat=None,postmat=None):

    if premat is not None:
        premat_param=f"--premat={premat}"
    else:
        premat_param=""
        
    if postmat is not None:
        postmat_param=f"--postmat={postmat}"
    else:
        post_param=""
    
    cmd=f"singularity run {neuroimg} applywarp"\
        f" --in={input}"\
        f" --ref={reference}"\
        f" --out={out}"\
        f" --warp={transwarp}"\
        f" --interp={interp}"\
        + premat_param + \
        + postmat_param 
    exit_code = check_call([cmd], shell=True)

def tkregister2_fslout(moving,target,neuroimg,outmat_fsl):
    cmd=f"singularity run {neuroimg} tkregister2"\
        f" --mov {moving}"\
        f" --targ {target}"\
        f" --regheader --reg junk --fslregout {outmat_fsl} --noedit"
    exit_code = check_call([cmd], shell=True)
    
def convMGZ2NII(mgz_in, nifti_out, neuroimg):
    cmd=f"singularity run {neuroimg} mri_convert"\
        f" --in_type mgz"\
        f" --out_type nii"\
        f" {mgz_in} {nifti_out}"
    exit_code = check_call([cmd], shell=True)
    
def disassembleTransforms(trans_in, trans_prefix, neuroimg):
    cmd=f"singularity run {neuroimg} --homedir={os.getcwd()} CompositeTransformUtil --disassemble"\
        f" {trans_in}"\
        f" {trans_prefix}"
    exit_code = check_call([cmd], shell=True)
    mats=glob.glob(os.path.join(os.getcwd(),f"*_{trans_prefix}_*"))
    return mats

def assembleTransforms(trans_in, trans_filename, neuroimg):
    if isinstance(trans_in,list):
        trans_string = " ".join(trans_in)
        cmd=f"singularity run {neuroimg} --homedir={os.getcwd()} CompositeTransformUtil --assemble"\
            f" {trans_filename}"\
            f" {trans_string}"
        exit_code = check_call([cmd], shell=True)
    else:
        print("list of transforms not passed. Skipping.")
        
def convertWarp_toFNIRT(ants_warp_field,fnirt_warp_field,source, neuroimg ):
    cmd=f"singularity run {neuroimg} wb_command -convert-warpfield"\
        f" -from-itk {ants_warp_field}"\
        f" -to-fnirt {fnirt_warp_field}"\
        f" {source}"   
    exit_code = check_call([cmd], shell=True)

def convertwarp_toANTS(fnirt_warp_field,source, ants_warp_field, neuroimg,absolute="" ):
    cmd=f"singularity run {neuroimg} wb_command -convert-warpfield"\
        f" -from-fnirt {fnirt_warp_field}"\
        f" {source}"\
        f" {absolute}"\
        f" -to-itk {ants_warp_field}"
    exit_code = check_call([cmd], shell=True)

def invertWarpfield_FNIRT(orig_source, fwd_warp_field, inv_warp_field, neuroimg):
    cmd=f"singularity run {neuroimg} invwarp"\
        f" --ref={orig_source}"\
        f" --warp={fwd_warp_field}"\
        f" --out={inv_warp_field}"
    exit_code = check_call([cmd], shell=True)
    
# absolute="-absolute" definitely did not work
def invertWarpfield_ANTS(ants_fwd_field, ants_inv_field, orig_source,orig_destination, neuroimg,absolute=""):
    fnirt_fwd_field = tempfile.mkstemp()[1] + ".nii.gz"
    convertWarp_toFNIRT(ants_fwd_field,fnirt_fwd_field,orig_source, neuroimg )
    
    fnirt_inv_field = tempfile.mkstemp()[1] + ".nii.gz"
    invertWarpfield_FNIRT(orig_source, fnirt_fwd_field, fnirt_inv_field , neuroimg)
    
    convertwarp_toANTS(fnirt_inv_field,orig_destination, ants_inv_field, neuroimg,absolute)

def invertAffine_FLIRT(fwd_affine, inv_affine, neuroimg):
    cmd=f"singularity run {neuroimg} comvert_xfm"\
        f" -omat {inv_affine}"\
        f" -inverse"\
        f" {fwd_affine}"
    exit_code = check_call([cmd], shell=True)

def invertAffine_ANTS(fwd_affine, inv_affine, moving, reference, neuroimg):
    fsl_fwd_affine = tempfile.mkstemp()[1] + ".mat"
    convert_affine_ants_to_fsl(fwd_affine, moving, reference,  fsl_fwd_affine)
    
    fsl_inv_affine = tempfile.mkstemp()[1] + ".mat"
    invertAffine_FLIRT(fsl_fwd_affine, fsl_inv_affine, neuroimg)
    
    convert_affine_fsl_to_ants(fsl_inv_affine, reference, moving, inv_affine)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        func=sys.argv[1]
        if func == "affine_ants_to_fsl":
            if len(sys.argv) > 5:
                antstrans_file=sys.argv[2]
                moving=sys.argv[3]
                refimg=sys.argv[4]
                fsltrans_file=sys.argv[5]
                convert_affine_ants_to_fsl(antstrans_file, moving, refimg, fsltrans_file)
        elif func == "ants_to_fsl":
            if len(sys.argv) > 5:
                antstrans_file=sys.argv[2]
                moving=sys.argv[3]
                refimg=sys.argv[4]
                fsltrans_file=sys.argv[5]
                convert_affine_ants_to_fsl(antstrans_file, moving, refimg, fsltrans_file)

