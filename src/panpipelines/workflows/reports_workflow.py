from nipype import Workflow, Node
from nipype.interfaces.io import DataSink

import panpipelines.nodes.reports as reports
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None,analysis_level='participant'):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    reports_node = reports.create(labels_dict,LOGGER=LOGGER,analysis_level=analysis_level)


    if analysis_level == 'participant':
        sinker_dir = getParams(labels_dict,"SINKDIR")
    else:
        sinker_dir = getParams(labels_dict,"SINKDIR_GROUP")

    if sinker_dir:
        sinker = Node(DataSink(),name='reports_sink')
        sinker_basedir = os.path.dirname(sinker_dir)
        sinker_folder = os.path.basename(sinker_dir)
        if not os.path.exists(sinker_basedir):
            os.makedirs(sinker_basedir,exist_ok=True)
        sinker.inputs.base_directory = sinker_basedir
        pan_workflow.connect( reports_node,"html_file",sinker,f"{sinker_folder}.@htmlfile")
    else:
        pan_workflow.add_nodes([reports_node])

    if createGraph:
        pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
