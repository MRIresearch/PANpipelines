from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

from dipy.core.gradients import gradient_table
import dipy.reconst.dti as dti
import dipy.reconst.fwdti as fwdti
import nibabel as nib
from dipy import __version__ as dipy_version

IFLOGGER=nlogging.getLogger('nipype.interface')

def freewater_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir = cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    if not session_label:
        search_session_label="*"
    else:
        search_session_label=session_label

    input_dir=substitute_labels(input_dir,labels_dict)
    dwi = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-preproc_dwi.nii.gz'))
    bval = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-preproc_dwi.bval'))
    bvec = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-preproc_dwi.bvec'))
    mask = getGlob(os.path.join(input_dir,'sub-{}'.format(participant_label),'ses-{}'.format(search_session_label),'dwi','*_desc-brain_mask.nii.gz'))

    freewater_dir = os.path.join(cwd,'freewater')
    if not os.path.isdir(freewater_dir):
        os.makedirs(freewater_dir,exist_ok=True)

    freeFA_dipy = os.path.join(freewater_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-freewater_desc-fa.nii.gz")
    freeFA_corrected_dipy = os.path.join(freewater_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-freewater_desc-facorrected.nii.gz")
    freeMD_dipy = os.path.join(freewater_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-freewater_desc-md.nii.gz")
    freeFrac_dipy = os.path.join(freewater_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-freewater_desc-fraction.nii.gz")

    dti_dir = os.path.join(cwd,'dti')
    if not os.path.isdir(dti_dir):
        os.makedirs(dti_dir,exist_ok=True)

    dtiFA_dipy = os.path.join(dti_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-fa.nii.gz")
    dtiFA_corrected_dipy = os.path.join(dti_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-facorrected.nii.gz")
    dtiMD_dipy = os.path.join(dti_dir,f"sub-{participant_label}_ses-{session_label}_space-T1w_desc-preproc_rec-dipy_desc-md.nii.gz")

    IFLOGGER.info("References:\n\nOfer Pasternak, Nir Sochen, Yaniv Gur, Nathan Intrator, and Yaniv Assaf. Free water elimination and mapping from diffusion MRI. Magnetic Resonance in Medicine, 62(3):717–730, 2009. URL: 10.1002/mrm.22055, doi:https://doi.org/10.1002/mrm.22055\n\nAndrew R. Hoy, Cheng Guan Koay, Steven R. Kecskemeti, and Andrew L. Alexander. Optimization of a free water elimination two-compartment model for diffusion tensor imaging. NeuroImage, 103:323–333, 2014. URL: 10.1016/j.neuroimage.2014.09.053, doi:https://doi.org/10.1016/j.neuroimage.2014.09.053.\n\nRafael Neto Henriques, Ariel Rokem, Eleftherios Garyfallidis, Samuel St-Jean, Eric Thomas Peterson, and Marta Morgado Correia. [Re] Optimization of a free water elimination two-compartment model for diffusion tensor imaging. bioRxiv, 2017. doi:https://doi.org/10.1101/108795.\n")

    IFLOGGER.info("See: https://docs.dipy.org/stable/examples_built/reconstruction/reconst_fwdti.html#sphx-glr-download-examples-built-reconstruction-reconst-fwdti-py")

    dwiimg = nib.load(dwi)
    maskimg = nib.load(mask)
    gtab = gradient_table(bvals=bval,bvecs=bvec)
    dwidata = np.asarray(dwiimg.dataobj)
    maskdata = maskimg.get_fdata()

    IFLOGGER.info(f"Calculating FreeWater Tensor Model using Dipy {dipy_version}")
  
    fwdtimodel = fwdti.FreeWaterTensorModel(gtab)
    fwdtifit = fwdtimodel.fit(dwidata, mask=maskdata)
    freeFA = fwdtifit.fa
    freeMD = fwdtifit.md
    freeFrac = fwdtifit.f

    FRAC_THRESHOLD = getParams(labels_dict,'FRAC_THRESHOLD')
    if not FRAC_THRESHOLD:
        FRAC_THRESHOLD=0.7
    freeFA_corrected=freeFA.copy()
    freeFA_corrected[freeFrac > FRAC_THRESHOLD]=0

    freeFAimg = nib.Nifti1Image(freeFA, dwiimg.affine, dwiimg.header)
    nib.save(freeFAimg,freeFA_dipy) 

    freeMDimg = nib.Nifti1Image(freeMD, dwiimg.affine, dwiimg.header)
    nib.save(freeMDimg,freeMD_dipy) 

    freeFracimg = nib.Nifti1Image(freeFrac, dwiimg.affine, dwiimg.header)
    nib.save(freeFracimg,freeFrac_dipy) 

    freeFAcorrectedimg = nib.Nifti1Image(freeFA_corrected, dwiimg.affine, dwiimg.header)
    nib.save(freeFAcorrectedimg,freeFA_corrected_dipy) 

    dtimodel = dti.TensorModel(gtab)
    dtifit = dtimodel.fit(dwidata, mask=maskdata)
    dtiFA = dtifit.fa
    dtiMD = dtifit.md
    dtiFA_corrected=dtiFA.copy()
    dtiFA_corrected[freeFrac > FRAC_THRESHOLD]=0

    dtiFAimg = nib.Nifti1Image(dtiFA, dwiimg.affine, dwiimg.header)
    nib.save(dtiFAimg,dtiFA_dipy) 

    dtiFAcorrectedimg = nib.Nifti1Image(dtiFA_corrected, dwiimg.affine, dwiimg.header)
    nib.save(dtiFAcorrectedimg,dtiFA_corrected_dipy) 

    dtiMDimg = nib.Nifti1Image(dtiMD, dwiimg.affine, dwiimg.header)
    nib.save(dtiMDimg,dtiMD_dipy) 

    out_files=[]
    out_files.insert(0,freeFA_dipy)
    out_files.insert(1,freeMD_dipy)
    out_files.insert(2,dtiFA_dipy)
    out_files.insert(3,dtiMD_dipy)


    return {
        "freefa":freeFA_dipy,
        "freemd":freeMD_dipy,
        "fraction":freeFrac_dipy,
        "dtifa":dtiFA_dipy,
        "dtimd":dtiMD_dipy,
        "output_dir":output_dir,
        "out_files":out_files
    }



class freewaterInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="QSIPREP Output Directory", usedefault=True)

class freewaterOutputSpec(TraitedSpec):
    freefa = File(desc='FreeFA')
    freemd = File(desc='FreeMD')
    fraction = File(desc='FreewaterFraction')
    dtifa = File(desc='dtiFA')
    dtimd = File(desc='dtiMD')
    output_dir = traits.String(desc="Freewater output directory")
    out_files = traits.List(desc='list of files')
    
class freewater_pan(BaseInterface):
    input_spec = freewaterInputSpec
    output_spec = freewaterOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = freewater_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="freewater_node",input_dir="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(freewater_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if input_dir is None:
        input_dir = ""
        
    pan_node.inputs.input_dir =  input_dir

    return pan_node


