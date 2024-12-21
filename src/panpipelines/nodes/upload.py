from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
from panpipelines.utils.upload_functions import *
import multiprocessing as mp
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def upload_proc(labels_dict,source_path,remote_path, ftpcredentials):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    pipeline = getParams(labels_dict,'PIPELINE')

    if ftpcredentials:
        with open(ftpcredentials,"r") as infile:
            ftpcred = json.load(infile)
            hostname=ftpcred["hostname"]
            username=ftpcred["username"]
            password=ftpcred["password"]
            if "port" in ftpcred.keys():
                port=int(ftpcred["password"])
            else:
                port = 22

    if source_path and remote_path and len(remote_path) == 1:
        IFLOGGER.info(f"Folders to upload {source_path} to {remote_path}")
        remote_path = [remote_path[0] for x in range(len(source_path))]
    elif not source_path:
        IFLOGGER.error(f"source_path not defined. cannot upload")
        raise Exception("upload.py : source_path not defined. Cannot upload")

    elif not remote_path:
        IFLOGGER.error(f"remote_path not defined. Cannot upload.")
        raise Exception("upload.py : remote_path not defined. Cannot upload")

    elif source_path and remote_path and not len(remote_path) == len(source_path):
        IFLOGGER.error(f"source path list {source_path} and remote path list {remote_path} do not match . Please ensure there is a 1:1 mapping or an N:1 mapping between source and remotes.")
        raise Exception("upload.py : length of source paths differs from remote paths and there are more than 1 remote paths.")

    retain_folder = isTrue( getParams(labels_dict,'RETAIN_FOLDER'))

    for source_path_dir,remote_path_dir in zip(source_path, remote_path):
        DEST_IS_DIR=False
        if os.path.isfile(source_path_dir):
            if remote_path_dir[-1]== "/":
                DEST_IS_DIR=True
                remote_path_dir = os.path.join(remote_path_dir,os.path.basename(source_path_dir))

            if retain_folder:
                remote_path_filename = os.path.basename(remote_path_dir)
                remote_path_dirname = os.path.dirname(remote_path_dir)
                source_path_folder = os.path.basename(os.path.dirname(source_path_dir))              
                remote_path_dir = os.path.join(remote_path_dirname,source_path_folder,remote_path_filename)
            

            ftp_upload(source_path_dir,remote_path_dir,hostname,username,password,port)
            remote_metadata_file = newfile(assocfile=os.path.dirname(remote_path_dir),suffix="upload-metadata",extension="json")
            local_metadata_file = newfile(outputdir=cwd,assocfile=remote_metadata_file,extension="json")
            
            metadata_init = {}
            history={}
            if DEST_IS_DIR:
                UPLOAD_SRC=source_path_dir
                UPLOAD_DEST=os.path.dirname(remote_path_dir )
            else:
                UPLOAD_SRC = source_path_dir
                UPLOAD_DEST = remote_path_dir 
            upload_metadata(local_metadata_file,remote_metadata_file,UPLOAD_SRC,UPLOAD_DEST,metadata=metadata_init,history=history,hostname=hostname,username=username,
            password=password, port=port)


        elif os.path.isdir(source_path_dir):
            if retain_folder:
                remote_path_dir = os.path.join(remote_path_dir,os.path.basename(source_path_dir))
            ftp_uploaddir_recursive(source_path_dir,remote_path_dir,hostname,username,password,port)

            remote_metadata_file = newfile(assocfile=os.path.dirname(remote_path_dir),suffix="upload-metadata",extension="json")
            local_metadata_file = newfile(outputdir=cwd,assocfile=remote_metadata_file,extension="json")
            
            metadata_init = {}
            history={}
            upload_metadata(local_metadata_file,remote_metadata_file,source_path_dir,remote_path_dir,metadata=metadata_init,history=history,hostname=hostname,username=username,
            password=password, port=port)

    out_files=[]
    out_files.append(local_metadata_file)

    return {
        "metadata_file" : local_metadata_file,
        "out_files" : out_files
    }

class uploadInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    source_path = traits.List([],desc="source path", usedefault=True)
    remote_path = traits.List([],desc="remote path", usedefault=True)
    ftpcredentials = traits.String("",desc="ftp credentials", usedefault=True)

class uploadOutputSpec(TraitedSpec):
    metadata_file = File(desc='metadata file for upload')
    out_files = traits.List(desc='list of files')

    
class upload_pan(BaseInterface):
    input_spec = uploadInputSpec
    output_spec = uploadOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = upload_proc(
            self.inputs.labels_dict,
            self.inputs.source_path,
            self.inputs.remote_path,
            self.inputs.ftpcredentials
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,source_path,remote_path, ftpcredentials, name='upload_node',LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(upload_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.source_path = source_path
    pan_node.inputs.remote_path = remote_path
    pan_node.inputs.ftpcredentials = ftpcredentials
   
    return pan_node


