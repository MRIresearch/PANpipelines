from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

def getprefix(custom_prefix, extra_prefix, add_prefix):
    prefix=""
    if add_prefix:
        if custom_prefix and extra_prefix:
            prefix=extra_prefix + "." + custom_prefix
        elif extra_prefix:
            prefix=extra_prefix 
    else:
        if custom_prefix:
            prefix=custom_prefix
    
    return prefix


def parse_textdata_proc(labels_dict, textdata, textdata_type,custom_prefix, add_prefix):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    
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
        os.makedirs(roi_output_dir,exist_ok=True)

    out_files=[]
    roi_csv = ""
    df=None
    basefile_name = os.path.basename(textdata)
    IFLOGGER.info(f"Data file {textdata} provided. Using {basefile_name} for csv output base.")

    current_pipeline = getParams(labels_dict,'PIPELINE')
    if not current_pipeline:
        current_pipeline = "Undetermined"

    # Need to think about this additional prefix - only included it because of the use case of comparing
    # different freesurfer pipelines. There should be a more elegant way to handle this.
    # Actually yes - just get the pipeline name or desc!
    subject_project = getParams(labels_dict,'PARTICIPANT_XNAT_PROJECT')
    if subject_project and subject_project in textdata:
        creating_pipeline = textdata.split("/" + subject_project)[0].split("/")[-1]
    else:
        creating_pipeline=""
        
    extra_prefix=""
    prefix=""
    use_creating_pipeline = isTrue(getParams(labels_dict,'USE_CREATING_PIPELINE_PREFIX'))
    if use_creating_pipeline:
        extra_prefix = creating_pipeline + "."

    override_add_prefix = isTrue(getParams(labels_dict,'OVERRIDE_ADD_PREFIX'))
    if override_add_prefix:
        add_prefix=True

    if "aseg" in basefile_name or textdata_type=="aseg":
        extra_prefix= extra_prefix + "aseg"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["Volume_mm3"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "lh.aparc.a2009s" in basefile_name or textdata_type=="lh.aparc.a2009s":
        extra_prefix= extra_prefix + "lh-Destrieux"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "rh.aparc.a2009s" in basefile_name or textdata_type=="rh.aparc.a2009s":
        extra_prefix= extra_prefix + "rh-Destrieux"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "lh.aparc" in basefile_name or textdata_type=="lh.aparc":
        extra_prefix= extra_prefix + "lh-DK"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "rh.aparc" in basefile_name or textdata_type=="rh.aparc":
        extra_prefix= extra_prefix + "rh-DK"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "lh.lobe" in basefile_name or textdata_type=="lh.lobe":
        extra_prefix= extra_prefix + "lh-lobe"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)
    elif "rh.lobe" in basefile_name or textdata_type=="rh.lobe":
        extra_prefix= extra_prefix + "rh-lobe"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label,session_label=session_label)      
    elif "hipposubfields.lh" in basefile_name or textdata_type=="hipposubfields.lh":
        extra_prefix= extra_prefix + "lh-hipposf" + basefile_name.split("hipposubfields.lh.")[1].split(".stats")[0].replace(".","-")
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_hippostats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "hipposubfields.rh" in basefile_name or textdata_type=="hipposubfields.rh":
        extra_prefix= extra_prefix+ "rh-hipposf" + basefile_name.split("hipposubfields.rh.")[1].split(".stats")[0].replace(".","-")
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_hippostats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "hippoSfVolumes" in basefile_name or textdata_type=="hippoSfVolumes":
        extra_prefix= extra_prefix+ basefile_name.split(".hippoSfVolumes")[0] + "-hippo" + basefile_name.split(".hippoSfVolumes")[1].split(".txt")[0].replace(".","-")
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "amygNucVolumes" in basefile_name or textdata_type=="amygNucVolumes":
        extra_prefix= extra_prefix + basefile_name.split(".amygNucVolumes")[0] + "-amyg" + basefile_name.split(".amygNucVolumes")[1].split(".txt")[0].replace(".","-")
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "ThalamicNuclei" in basefile_name or textdata_type=="ThalamicNuclei":
        extra_prefix= extra_prefix+ "thalamic" + basefile_name.split("ThalamicNuclei")[1].split(".volumes.txt")[0].replace(".","-")
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "brainstemSsLabelsbeta" in basefile_name or textdata_type=="brainstembeta":
        extra_prefix= extra_prefix + "brainstembeta"
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "bold.json" in basefile_name or textdata_type=="mriqc_bold":
        extra_prefix= extra_prefix + "bold" 
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,'MRIQC_BOLD_COLS')
        df = get_jsonstats(textdata,extract_columns=extract_columns, prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "T1w.json" in basefile_name or textdata_type=="mriqc_t1w":
        extra_prefix= extra_prefix + "t1w" 
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,'MRIQC_T1W_COLS')
        df = get_jsonstats(textdata,extract_columns=extract_columns, prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "T2w.json" in basefile_name or textdata_type=="mriqc_t2w":
        extra_prefix= extra_prefix + "t2w" 
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,'MRIQC_T2W_COLS')
        df = get_jsonstats(textdata,extract_columns=extract_columns, prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "dwi.json" in basefile_name or textdata_type=="mriqc_dwi":
        extra_prefix= extra_prefix + "dwi" 
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,'MRIQC_DWI_COLS')
        df = get_jsonstats(textdata,extract_columns=extract_columns, prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "QC_collection" in basefile_name or textdata_type=="exploreasl_qc":
        extra_prefix= extra_prefix + "exploreasl_qc" 
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,'EXPLOREASL_QC_COLS')
        df = get_jsonstats(textdata,extract_columns=extract_columns, prefix=prefix, participant_label=participant_label,session_label=session_label)
    elif "qualitycontrol_cbf.csv" in basefile_name or textdata_type=="aslprep_qc":
        extra_prefix= extra_prefix + "aslprep_qc" 
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,'ASLPREP_QC_COLS')

        delimiter = getParams(labels_dict,'TEXT_DELIMITER')
        if delimiter:
            delimiter = delimiter
        else:
            delimiter=","

        df = get_csvstats(textdata,extract_columns=extract_columns, prefix=prefix, participant_label=participant_label,session_label=session_label,delimiter=delimiter)
    elif ".txt" in basefile_name or textdata_type=="singletext":
        prefix = getprefix(custom_prefix, extra_prefix, add_prefix)
        extract_columns = getParams(labels_dict,"TEXT_COLS")

        delimiter = getParams(labels_dict,'TEXT_DELIMITER')
        if delimiter:
            delimiter = delimiter
        else:
            delimiter='\s+'

        df = get_text(textdata, extract_columns=extract_columns, prefix=prefix,participant_label=participant_label, session_label=session_label,delimiter=delimiter)
 
    else:
        IFLOGGER.info("basename {textdata} not implemented.")


    if df is not None:
        #process extra columns
        df = processExtraColumns(df, labels_dict)

        # Add creation date
        created_datetime = get_datetimestring_utc()
        df.insert(len(df.columns),"row_creation_datetime",[created_datetime for x in range(len(df))])

        if NOSESSION:
            roi_csv = os.path.join(roi_output_dir,'{}_{}_{}.csv'.format("sub-"+participant_label,creating_pipeline,prefix))
        else:
            roi_csv = os.path.join(roi_output_dir,'{}_{}_{}_{}.csv'.format("sub-"+participant_label,"ses-"+session_label,creating_pipeline,prefix))            
        df.to_csv(roi_csv,sep=",",header=True, index=False)
        out_files.insert(0,roi_csv)

        metadata = {}
        metadata = updateParams(metadata,"Title","parse_textdata.py")
        metadata = updateParams(metadata,"Description","Parse textdata from existing tables into csv using predefined approaches. Freesurfer stat files are supported.")
        metadata = updateParams(metadata,"Pipeline",f"{current_pipeline}")
        metadata = updateParams(metadata,"Prefix",f"{prefix}")
        metadata = updateParams(metadata,"InputFile",f"{textdata}")
        metadata = updateParams(metadata,"InputFilePipeline",f"{creating_pipeline}")
        roi_csv_json = create_metadata(roi_csv, created_datetime, metadata = metadata)


    return {
        "roi_csv":roi_csv,
        "roi_csv_metadata":roi_csv_json,
        "roi_output_dir":roi_output_dir,
        "output_dir":output_dir,
        "out_files":out_files
    }



class parse_textdataInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    textdata = File(desc='text data file to parse')
    textdata_type = traits.String(desc='type of file to help discern parsing method')
    custom_prefix = traits.String(desc='Prefix to add to columns')
    add_prefix = traits.Bool(False,desc="Add automatic prefux",usedefault=True)

class parse_textdataOutputSpec(TraitedSpec):
    roi_csv = File(desc='CSV file of results')
    roi_csv_metadata = File(desc='Metadata CSV file of results')
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
            self.inputs.textdata_type,
            self.inputs.custom_prefix,
            self.inputs.add_prefix
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="parse_textdata_node",textdata="",textdata_type="",custom_prefix="",add_prefix=False,LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(parse_textdata_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
            
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if not textdata:
        pan_node.inputs.textdata = textdata
 
    if not textdata_type:
        pan_node.inputs.textdata_type = textdata_type    

    if not custom_prefix:
        pan_node.inputs.custom_prefix = custom_prefix 

    pan_node.inputs.add_prefix =  add_prefix            

    return pan_node


