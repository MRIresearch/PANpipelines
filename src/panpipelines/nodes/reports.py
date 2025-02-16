from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import multiprocessing as mp
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging
from panpipelines.utils.report_functions import *

IFLOGGER=nlogging.getLogger('nipype.interface')

def reports_proc(labels_dict,analysis_level):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    html_file_dir = os.path.join(cwd,f"html_report")
    if not os.path.isdir(html_file_dir ):
        os.makedirs(html_file_dir,exist_ok=True)


    reports_source  = getParams(labels_dict,'REPORTS_SOURCE')
    if reports_source:
        reports_source = getGlob(reports_source)
    reports_pipeline_class = getParams(labels_dict,'REPORTS_PIPELINECLASS')
    reports_pipeline = getParams(labels_dict,'REPORTS_PIPELINE')
    if not reports_pipeline:
        reports_pipeline = "unknown-pipeline"


    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    if participant_label:
        html_name = f"sub-{participant_label}_ses-{session_label}_{reports_pipeline}.html"
    else:
        html_name = f"{reports_pipeline}.html"


    if reports_pipeline_class == "roiextract_panpipeline":
        html_file = newfile(outputdir=html_file_dir, assocfile = reports_source , suffix="htmlreport",extension="html")
        html_file = createRoiExtractReport(labels_dict,html_file, reports_source,analysis_level=analysis_level)
    elif reports_pipeline_class == "basil_panpipeline":
        html_file = newfile(outputdir=html_file_dir, assocfile = html_name, suffix="htmlreport",extension="html")
        html_file = createBasilReport(labels_dict,html_file, reports_source,analysis_level=analysis_level)


    out_files=[]
    out_files.insert(0,html_file)


    return {
        "html_file" : html_file,
        "out_files" : out_files
    }

class reportsInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    analysis_level = traits.String("participant",desc="analysis level", usedefault=True)

class reportsOutputSpec(TraitedSpec):
    html_file = File(desc='html file used for results')
    out_files = traits.List(desc='list of files')
    
class reports_pan(BaseInterface):
    input_spec = reportsInputSpec
    output_spec = reportsOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = reports_proc(
            self.inputs.labels_dict,
            self.inputs.analysis_level
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict, name='reports_node',LOGGER=IFLOGGER,analysis_level='participant'):
    # Create Node
    pan_node = Node(reports_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    pan_node.inputs.analysis_level = analysis_level
   
    return pan_node


