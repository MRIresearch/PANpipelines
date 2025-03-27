from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
from nipype import logging as nlogging
import pysftp

UTLOGGER=nlogging.getLogger('nipype.utils')

def ftp_exists(remote_path,hostname,username,password,port):
    with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
        return connection.exists(remote_path)
  
def ftp_listdir(remote_path,hostname,username,password,port):
    files_and_dirs=[]
    with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
        files_and_dirs = connection.listdir(remote_path)
    return files_and_dirs

def ftp_listdir_attr(remote_path,hostname,username,password,port):
    files_and_dirs=[]
    with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
        files_and_dirs  =  connection.listdir_attr(remote_path)
    return files_and_dirs

def ftp_download(remote_path, target_local_path,hostname,username,password,port):
    try:
        # Create the target directory if it does not exist
        if not os.path.isdir(os.path.dirname(target_local_path)):
            try:
                os.makedirs(os.path.dirname(target_local_path),exist_ok=True)
            except Exception as err:
                raise Exception(err)
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            connection.get(remote_path, target_local_path)
    except Exception as err:
        raise Exception(err)

def ftp_downloaddir_recursive(remote_path, target_local_path,hostname,username,password,port):
    try:
        # Create the target directory if it does not exist
        path, _ = os.path.split(target_local_path)
        if not os.path.isdir(path):
            try:
                os.makedirs(path,exist_ok=True)
            except Exception as err:
                raise Exception(err)
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            connection.chdir(os.path.dirname(remote_path))
            basefolder = os.path.basename(remote_path)
            connection.get_r(basefolder, path)
    except Exception as err:
        raise Exception(err)

def ftp_upload(source_local_path, remote_path,hostname,username,password,port):
    try:
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            if not connection.exists(os.path.dirname(remote_path)):
                connection.makedirs(os.path.dirname(remote_path))
            connection.put(source_local_path, remote_path)
    except Exception as err:
        raise Exception(err)

def ftp_uploaddir_recursive(source_local_path, remote_path,hostname=None,username=None,password=None,port=None):
    try:
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            if not connection.exists(remote_path):
                connection.makedirs(remote_path)
            connection.put_r(source_local_path, remote_path)
    except Exception as err:
        raise Exception(err)


def ftp_upload_subjectbids(subject_dir, remote_path,hostname=None,username=None,password=None, port=None, replace=True):
    subject = os.path.basename(subject_dir)
    print(f"uploading {subject} from {subject_dir} to {remote_path}.")
    if ftp_exists(remote_path,hostname,username,password,port) and replace:
        print(f"{remote_path} already exists. Will remove before uploading {subject}")
        ftp_deletedir_recursive(remote_path,hostname,username,password,port)
        print(f"{remote_path} successfully deleted.")
        
    ftp_uploaddir_recursive(subject_dir, remote_path,hostname=hostname,username=username,password=password,port=port)
    print(f"{subject} successfully uploaded.")

def ftp_upload_allbids(bids_dir, remote_path,hostname=None,username=None,password=None,port=None):
    ftp_uploaddir_recursive(bids_dir,remote_path,hostname,username,password,port)
    remote_participantsTSV=os.path.join(remote_path,"participants.tsv")
    local_participantsTSV = os.path.join(bids_dir,"participants.tsv")
    metadata = {}
    local_metadata_file = newfile(assocfile=local_participantsTSV,extension="json")
    if os.path.exists(local_metadata_file):
        with open(local_metadata_file,"r") as infile:
            metadata = json.load(infile)

    history={}
    history["SourceBIDS"]=f"{bids_dir}"
    history["TargetBIDS"]=f"{remote_path}"
    date_uploaded = get_datetimestring_utc()
    history["Description"]=f"All bids files uploaded from {bids_dir}"
    r_file = newfile(assocfile=remote_participantsTSV,extension="json")
    tmpJsonFile = get_upload_metadata(r_file, local_participantsTSV,remote_participantsTSV,date_uploaded,metadata=metadata,history=history)
    ftp_upload(tmpJsonFile,r_file,hostname,username,password,port)

def ftp_delete(remote_path,hostname,username,password,port):
    try:
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            connection.remove(remote_path)
    except Exception as err:
        raise Exception(err)

def ftp_deletedir(remote_path,hostname,username,password,port):
    try:
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            connection.rmdir(remote_path)
    except Exception as err:
        raise Exception(err)

def ftp_deletedir_recursive(remote_path,hostname,username,password,port):
    dirs=[remote_path]
    try:
        with pysftp.Connection(host=hostname,username=username,password=password,port=port) as connection:
            connection.walktree(dirs[0], fcallback=connection.remove, dcallback=dirs.append, ucallback=connection.remove, recurse=True)
            for d in reversed(dirs):
                connection.rmdir(d)
    except Exception as err:
        raise Exception(err)


def get_upload_metadata(metadata_file, upload_source = None, upload_destination=None, date_uploaded = None, creator=None, metadata={},history={}):

    metadata = updateParams(metadata,"MetadataFile",f"{metadata_file}")

    if not date_uploaded:
        date_uploaded = get_datetimestring_utc()
    metadata["LastUpload"] = date_uploaded

    if not "History" in metadata.keys():
        metadata["History"]={}

    if not date_uploaded in metadata["History"].keys():
        metadata["History"][date_uploaded] = {}

    if upload_source:
        metadata = updateParams(metadata,"UploadSource",f"{upload_source}")
        metadata["History"][date_uploaded]["UploadSource"] = f"{upload_source}"

    if upload_destination:
        metadata = updateParams(metadata,"UploadDestination",f"{upload_destination}")
        metadata["History"][date_uploaded]["UploadDestination"] = f"{upload_destination}"


    if not creator:
        if "USER" in os.environ.keys():
            metadata["History"][date_uploaded]["UploadedBy"] = os.environ["USER"]
        else:
            metadata["History"][date_uploaded]["UploadedBy"] = "Unknown"

    if "HOSTNAME" in os.environ.keys():
        metadata["History"][date_uploaded]["Hostname"] = os.environ["HOSTNAME"]

    metadata["History"][date_uploaded]["IP"] = get_ip()

    for itemkey, itemvalue in history.items():
        metadata["History"][date_uploaded][itemkey]=itemvalue
        
    tmp_json = tempfile.mkstemp()[1] + os.path.basename(metadata_file)
    export_labels(metadata,tmp_json)

    return tmp_json

def upload_metadata(local_metadata_file,remote_metadata_file,upload_source,upload_destination,metadata={},history={},date_uploaded=None,hostname=None,username=None,password=None, port=None):
    try:
        tmp_json_file = tempfile.mkstemp()[1] + os.path.basename(remote_metadata_file)
        ftp_download(remote_metadata_file,tmp_json_file,hostname,username,password,port)
        if tmp_json_file and os.path.exists(tmp_json_file):
            with open(tmp_json_file,'r') as infile:
                prev_metadata = json.load(infile)
                for itemkey,itemvalue in prev_metadata.items():
                    if not itemkey in metadata.keys():
                        metadata[itemkey]=itemvalue
    except Exception as e:
        pass
        
    tmpJsonFile = get_upload_metadata(remote_metadata_file,upload_source ,upload_destination,date_uploaded,metadata=metadata,history=history)
    ftp_upload(tmpJsonFile,remote_metadata_file,hostname,username,password,port)

    shutil.copy(tmpJsonFile,local_metadata_file)

    return local_metadata_file
