from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def parse_textdata_proc(labels_dict, textdata, textdata_type):

    cwd=os.getcwd()
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    roi_output_dir = os.path.join(cwd,'{}_roi_output_dir'.format(participant_label))

    NOSESSION=False
    if not session_label:
        session_label = "NotProvided"
        NOSESSION=True
    else:
        roi_output_dir = os.path.join(cwd,'{}_{}_roi_output_dir'.format(participant_label,session_label))

    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    out_files=[]
    roi_csv = None
    df=None
    basefile_name = os.path.basename(textdata)
    IFLOGGER.info(f"Data file {textdata} provided. Using {basefile_name} for csv output base.")


    pipeline_name = getParams(labels_dict,'PIPELINE')
    if not pipeline_name:
        pipeline_name="UnDetermined"

    # Need to think about this additional prefix - only included it because of the use case of comparing
    # different freesurfer pipelines. There should be a more elegant way to handle this.
    # Actually yes - just get the pipeline name or desc!
    subject_project = getParams(labels_dict,'PARTICIPANT_XNAT_PROJECT')
    if subject_project:
        creating_pipeline = textdata.split("/" + subject_project)[0].split("/")[-1]
    else:
        creating_pipeline=""
        
    addpref=""
    if creating_pipeline:
        addpref = creating_pipeline + "-"

    if "aseg" in basefile_name or textdata_type=="aseg":
        prefix= addpref + "aseg"
        df = get_freesurfer_genstats(textdata,columns=["Volume_mm3"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "lh.aparc.a2009s" in basefile_name or textdata_type=="lh.aparc.a2009s":
        prefix= addpref + "lh-Destrieux"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "rh.aparc.a2009s" in basefile_name or textdata_type=="rh.aparc.a2009s":
        prefix= addpref + "rh-Destrieux"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "lh.aparc" in basefile_name or textdata_type=="lh.aparc":
        prefix= addpref + "lh-DK"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "rh.aparc" in basefile_name or textdata_type=="rh.aparc":
        prefix= addpref + "rh-DK"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)     
    elif "hipposubfields.lh" in basefile_name or textdata_type=="hipposubfields.lh":
        prefix= addpref + "lh-hipposf" + basefile_name.split("hipposubfields.lh.")[1].split(".stats")[0].replace(".","-")
        df = get_freesurfer_hippostats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "hipposubfields.rh" in basefile_name or textdata_type=="hipposubfields.rh":
        prefix= addpref + "rh-hipposf" + basefile_name.split("hipposubfields.rh.")[1].split(".stats")[0].replace(".","-")
        df = get_freesurfer_hippostats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "hippoSfVolumes" in basefile_name or textdata_type=="hippoSfVolumes":
        prefix =  addpref + basefile_name.split(".hippoSfVolumes")[0] + "-hippo" + basefile_name.split(".hippoSfVolumes")[1].split(".txt")[0].replace(".","-")
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "amygNucVolumes" in basefile_name or textdata_type=="amygNucVolumes":
        prefix =  addpref + basefile_name.split(".amygNucVolumes")[0] + "-amyg" + basefile_name.split(".amygNucVolumes")[1].split(".txt")[0].replace(".","-")
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "ThalamicNuclei" in basefile_name or textdata_type=="ThalamicNuclei":
        prefix =  addpref + "thalamic" + basefile_name.split("ThalamicNuclei")[1].split(".volumes.txt")[0].replace(".","-")
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "brainstemSsLabelsbeta" in basefile_name or textdata_type=="brainstembeta":
        prefix =  addpref + "brainstembeta"
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    else:
        IFLOGGER.info("basename {textdata} not implemented.")


    if df is not None:
        if NOSESSION:
            roi_csv = os.path.join(roi_output_dir,'{}_{}_{}.csv'.format(participant_label,pipeline_name,basefile_name))
        else:
            roi_csv = os.path.join(roi_output_dir,'{}_{}_{}_{}.csv'.format(participant_label,session_label,pipeline_name,basefile_name))            
        df.to_csv(roi_csv,sep=",",header=True, index=False)
        out_files.insert(0,roi_csv)

        metadata = {}
        roi_csv_json = os.path.splitext(roi_csv)[0] + ".json"
        metadata = updateParams(metadata,"Title","parse_textdata.py")
        metadata = updateParams(metadata,"Description","Parse textdata from existing tables into csv using predefined approaches. Freesurfer stat files are supported.")
        metadata = updateParams(metadata,"MetadataFile",f"{roi_csv_json}")
        metadata = updateParams(metadata,"FileCreated",f"{roi_csv}")
        metadata = updateParams(metadata,"DateCreated",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f"))
        metadata = updateParams(metadata,"Pipeline",f"{pipeline_name}")
        metadata = updateParams(metadata,"InputFile",f"{textdata}")
        metadata = updateParams(metadata,"InputFilePipeline",f"{creating_pipeline}")
        export_labels(metadata,roi_csv_json)

    return {
        "roi_csv":roi_csv,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class parse_textdataInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    textdata = File(desc='text data file to parse')
    textdata_type = traits.String(desc='type of file to help discern parsing method')

class parse_textdataOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    roi_output_dir = traits.String(desc='roi output dir')
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class parse_textdata_pan(BaseInterface):
    input_spec = parse_textdataInputSpec
    output_spec = parse_textdataOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = parse_textdata_proc(
            self.inputs.labels_dict,
            self.inputs.textdata,
            self.inputs.textdata_type
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="parse_textdata_node",textdata="",textdata_type="",LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(parse_textdata_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
            
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if not textdata is None and not textdata == "":
        pan_node.inputs.textdata = textdata
 
    if not textdata_type is None and not textdata_type == "":
        pan_node.inputs.textdata_type = textdata_type                

    return pan_node


