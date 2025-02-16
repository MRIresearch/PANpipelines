from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
from nipype import logging as nlogging
from scipy.io import savemat 
import gzip
from bids import BIDSLayout
import shutil
import numpy as np

IFLOGGER=nlogging.getLogger('nipype.interface')

def prepare_bidsfile(layout,subject,suffix,datadir):
    mod=layout.get(subject=subject,suffix=suffix, extension='nii.gz')

    if len(mod)>0:
        mod_path=mod[0].path
        mod_file=mod[0].filename
        print("{} image found. Using {}\n\n".format(suffix,mod_file))
        if len(mod) > 1:
            print("Multiple {} images found. Using {}\n\n".format(suffix,mod_file))
            print("{} files found were:".format(mod))
            print('\n'.join([x.path for x in mod]))
 
        try:
            mod_newpath=os.path.join(datadir,mod_file)
            shutil.copyfile(mod_path,mod_newpath)
            print("Copying file from {} to {}".format(mod_path,mod_newpath))

            mod_newpath_nii=mod_newpath.split('.nii.gz')[0] + '.nii'
            decompress(mod_newpath,mod_newpath_nii,"gzip-clean")
            print("Decompressing {} in place to {}".format(mod_newpath,mod_newpath_nii))
            return mod_newpath_nii
        except Exception as e:
            print("Problem copying {} to {} and decompressing to {}".format(mod_path,mod_newpath,mod_newpath_nii))
            print(e)
            return None

    else:
        print("{} image not found".format(mod))
        return None

def create_lpa(matfile,flair,OPT=''):
    matlabbatch = np.zeros((1,),dtype=object) 
    matlabbatch[0]={}
    matlabbatch[0]['spm']={}
    matlabbatch[0]['spm']['tools']={}
    matlabbatch[0]['spm']['tools']['LST']={}
    matlabbatch[0]['spm']['tools']['LST']['lpa']={}

    file2 = np.zeros((1,),dtype=object)
    file2[0]='{},1'.format(flair)
    matlabbatch[0]['spm']['tools']['LST']['lpa']['data_F2']=[file2]

    opt = np.zeros((1,),dtype=object) 
    opt[0]=OPT         
    matlabbatch[0]['spm']['tools']['LST']['lpa']['data_coreg']=[opt]
    matlabbatch[0]['spm']['tools']['LST']['lpa']['html_report']=1 
    savemat(matfile,{'matlabbatch':matlabbatch})
    print("Created {}".format(matfile))


def create_lga(matfile,t1w,flair,INIT=300,MRF=1,MAXITER=50,HTML=1):
    matlabbatch = np.zeros((1,),dtype=object) 
    matlabbatch[0]={}
    matlabbatch[0]['spm']={}
    matlabbatch[0]['spm']['tools']={}
    matlabbatch[0]['spm']['tools']['LST']={}
    matlabbatch[0]['spm']['tools']['LST']['lga']={}

    file1 = np.zeros((1,),dtype=object)
    file1[0]='{},1'.format(t1w)
    matlabbatch[0]['spm']['tools']['LST']['lga']['data_T1']=[file1]

    file2 = np.zeros((1,),dtype=object)
    file2[0]='{},1'.format(flair)
    matlabbatch[0]['spm']['tools']['LST']['lga']['data_F2']=[file2]
                
    matlabbatch[0]['spm']['tools']['LST']['lga']['opts_lga']={}
    matlabbatch[0]['spm']['tools']['LST']['lga']['opts_lga']['initial']=INIT
    matlabbatch[0]['spm']['tools']['LST']['lga']['opts_lga']['mrf']=MRF  
    matlabbatch[0]['spm']['tools']['LST']['lga']['opts_lga']['maxiter']=MAXITER
    matlabbatch[0]['spm']['tools']['LST']['lga']['html_report']=HTML 
    savemat(matfile,{'matlabbatch':matlabbatch})
    print("Created {}".format(matfile))

def decompress(infile, outfile, type):
    if type == 'gzip-clean':
        with open(infile,'rb') as fi:
            indata=fi.read()

        os.remove(infile)
        
        indata_dec=gzip.decompress(indata)
        with open(outfile,'wb') as fo:
            fo.write(indata_dec)

def compress(infile, outfile, type):
    if type == 'gzip-clean':
        with open(infile,'rb') as fi:
            with gzip.open(outfile,'wb') as fo:
                shutil.copyfileobj(fi,fo)
        os.remove(infile)

    elif type == 'gzip':
        with open(infile,'rb') as fi:
            with gzip.open(outfile,'wb') as fo:
                shutil.copyfileobj(fi,fo)


def lst_proc(labels_dict,bids_dir=""):
    
    command_base, container = getContainer(labels_dict,nodename="lst",SPECIFIC="LST_CONTAINER",LOGGER=IFLOGGER)

    cwd=os.getcwd()
    lst_type = getParams(labels_dict,"LST_TYPE")
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    output_dir=os.path.join(cwd,'sub-' + participant_label,lst_type)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir,exist_ok=True)

    data_dir=os.path.join(output_dir,'data')
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir,exist_ok=True)

    labels_dict = updateParams(labels_dict,"CWD",cwd)
    labels_dict = updateParams(labels_dict,"LST_OUTPUT_DIR",output_dir)

    IFLOGGER.info(f"Running the {lst_type} algorithm for {participant_label}")

    layout = BIDSLayout(bids_dir)
    if lst_type == "LGA":
        T1w = prepare_bidsfile(layout,participant_label,'T1w',data_dir)
        FLAIR =  prepare_bidsfile(layout,participant_label,'FLAIR',data_dir)
        if FLAIR is None or T1w is None:
            IFLOGGER.info(f"FLAIR or T1w is missing. Not enough data to run {lst_type}. Returning")
            return
        else:
            matfile=os.path.join(output_dir,participant_label + f'_{lst_type}.mat')
            create_lga(matfile,T1w,FLAIR)

    elif lst_type == 'LPA':
        FLAIR =  prepare_bidsfile(layout,participant_label,'FLAIR',data_dir)
        if FLAIR is None :
            IFLOGGER.info(f"FLAIR is missing. Not enough data to run {lst_type}. Returning")
            return
        else:
            matfile=os.path.join(output_dir,participant_label + f'_{lst_type}.mat')
            create_lpa(matfile,FLAIR)

    params = f"{matfile}"   

    command = f"{command_base} run_jobman"\
        " "+params 

    evaluated_command=substitute_labels(command,labels_dict)
    results = runCommand(evaluated_command,IFLOGGER)

    ples_nii = getGlob(os.path.join(data_dir,'ples_*.nii'))
    ples = ples_nii + '.gz'
    compress(ples_nii,ples,"gzip-clean")

    msub_nii = getGlob(os.path.join(data_dir,'*msub*.nii'))
    msub = msub_nii + '.gz'
    compress(msub_nii,msub,"gzip-clean")
    

    out_files=[]
    out_files.insert(0,ples)
    out_files.insert(1,msub)


    return {
        "ples": ples,
        "msub": msub,
        "output_dir":output_dir,
        "out_files":out_files
    }



class lstInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    bids_dir = traits.String("",desc="BIDS Directory", usedefault=True)

class lstOutputSpec(TraitedSpec):
    ples= File(desc='ples')
    msub = File(desc='msub')
    output_dir = traits.String(desc="lst output directory")
    out_files = traits.List(desc='list of files')
    
class lst_pan(BaseInterface):
    input_spec = lstInputSpec
    output_spec = lstOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = lst_proc(
            self.inputs.labels_dict,
            self.inputs.bids_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='lst_node',bids_dir="", LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(lst_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    if bids_dir is None or bids_dir == "":
        bids_dir = substitute_labels("<BIDS_DIR>", labels_dict)

    pan_node.inputs.bids_dir =  bids_dir

    return pan_node


