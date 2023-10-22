from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib

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
    if "aseg" in basefile_name or textdata_type=="aseg":
        df = get_freesurfer_genstats(textdata,columns=["Volume_mm3"], prefix="aseg",participant_label=participant_label)
    if "lh.aparc.a2009s" in basefile_name or textdata_type=="lh.aparc.a2009s":
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix="lh-Destrieux",participant_label=participant_label)
    if "rh.aparc.a2009s" in basefile_name or textdata_type=="rh.aparc.a2009s":
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix="rh-Destrieux",participant_label=participant_label)
    if "lh.aparc" in basefile_name or textdata_type=="lh.aparc":
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix="lh-DK",participant_label=participant_label)
    if "rh.aparc" in basefile_name or textdata_type=="rh.aparc":
        df = get_freesurfer_genstats(textdata,columns=["SurfArea","GrayVol","ThickAvg"], prefix="rh-DK",participant_label=participant_label)     
    if "hipposubfields.lh" in basefile_name or textdata_type=="hipposubfields.lh":
        df = get_freesurfer_hippostats(textdata,prefix="lh-hipposf", participant_label=participant_label)
    if "hipposubfields.rh" in basefile_name or textdata_type=="hipposubfields.rh":
        df = get_freesurfer_hippostats(textdata,prefix="rh-hipposf", participant_label=participant_label)


    if df is not None:
        roi_csv = os.path.join(roi_output_dir,'{}_{}.csv'.format(participant_label,basefile_name))
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


def create(labels_dict,name="parse_textdata_node",textdata="",textdata_type=""):
    # Create Node
    pan_node = Node(parse_textdata_pan(), name=name)
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict

    if not textdata is None and not textdata == "":
        pan_node.inputs.textdata = textdata
 
    if not textdata_type is None and not textdata_type == "":
        pan_node.inputs.textdata_type = textdata_type                

    return pan_node


