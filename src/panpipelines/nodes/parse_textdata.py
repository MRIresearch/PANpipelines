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

    roi_output_dir = os.path.join(cwd,'{}_roi_output_dir'.format(participant_label))
    if not os.path.isdir(roi_output_dir):
        os.makedirs(roi_output_dir)

    out_files=[]
    roi_csv = None
    df=None
    basefile_name = os.path.basename(textdata)
    IFLOGGER.info("basename {textdata} provided.")

    # Need to think about this additional prefix - only included it because of the use case of comparing
    # different freesurfer pipelines. There should be a more elegant way to handle this.
    subject_project = getParams(labels_dict,'PARTICIPANT_XNAT_PROJECT')
    if subject_project:
        addpref = textdata.split("/" + subject_project)[0].split("/")[-1]
    else:
        addpref=""

    if "aseg" in basefile_name or textdata_type=="aseg":
        prefix= addpref + "-" + "aseg"
        df = get_freesurfer_genstats(textdata,columns=["Volume_mm3"], prefix=prefix,participant_label=participant_label)
    elif "lh.aparc.a2009s" in basefile_name or textdata_type=="lh.aparc.a2009s":
        prefix= addpref + "-" + "lh-Destrieux"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label)
    elif "rh.aparc.a2009s" in basefile_name or textdata_type=="rh.aparc.a2009s":
        prefix= addpref + "-" + "rh-Destrieux"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label)
    elif "lh.aparc" in basefile_name or textdata_type=="lh.aparc":
        prefix= addpref + "-" + "lh-DK"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label)
    elif "rh.aparc" in basefile_name or textdata_type=="rh.aparc":
        prefix= addpref + "-" + "rh-DK"
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix=prefix,participant_label=participant_label)     
    elif "hipposubfields.lh" in basefile_name or textdata_type=="hipposubfields.lh":
        prefix= addpref + "-" + "lh-hipposf" + basefile_name.split("hipposubfields.lh.")[1].split(".stats")[0].replace(".","-")
        df = get_freesurfer_hippostats(textdata,prefix=prefix, participant_label=participant_label)
    elif "hipposubfields.rh" in basefile_name or textdata_type=="hipposubfields.rh":
        prefix= addpref + "-" + "rh-hipposf" + basefile_name.split("hipposubfields.rh.")[1].split(".stats")[0].replace(".","-")
        df = get_freesurfer_hippostats(textdata,prefix=prefix, participant_label=participant_label)
    elif "hippoSfVolumes" in basefile_name or textdata_type=="hippoSfVolumes":
        prefix =  addpref + "-" + basefile_name.split(".hippoSfVolumes")[0] + "-hippo" + basefile_name.split(".hippoSfVolumes")[1].split(".txt")[0].replace(".","-")
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label)
    elif "amygNucVolumes" in basefile_name or textdata_type=="amygNucVolumes":
        prefix =  addpref + "-" + basefile_name.split(".amygNucVolumes")[0] + "-amyg" + basefile_name.split(".amygNucVolumes")[1].split(".txt")[0].replace(".","-")
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label)
    elif "ThalamicNuclei" in basefile_name or textdata_type=="ThalamicNuclei":
        prefix =  addpref + "-" + "thalamic" + basefile_name.split("ThalamicNuclei")[1].split(".volumes.txt")[0].replace(".","-")
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label)
    elif "brainstemSsLabelsbeta" in basefile_name or textdata_type=="brainstembeta":
        prefix =  addpref + "-" + "brainstembeta"
        df = get_freesurfer_subregionstats(textdata,prefix=prefix, participant_label=participant_label)
    else:
        IFLOGGER.info("basename {textdata} not implemented.")


    if df is not None:
        roi_csv = os.path.join(roi_output_dir,'{}_{}_{}.csv'.format(addpref,participant_label,basefile_name))
        df.to_csv(roi_csv,sep=",",header=True, index=False)
        out_files.insert(0,roi_csv)

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


