from nipype import Workflow

import panpipelines.nodes.tractseg as tractseg
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    qsiprep_input_dir = getParams(labels_dict,"QSIPREP_OUTPUT_DIR")
    tractseg_node = tractseg.create(labels_dict, input_dir=qsiprep_input_dir,LOGGER=LOGGER)

    pan_workflow.add_nodes([tractseg_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
