from nipype import Workflow

import panpipelines.nodes.xcpd as xcpd
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    fmriprep_input_dir = getParams(labels_dict,"FMRIPREP_OUTPUT_DIR")
    xcpd_node = xcpd.create(labels_dict, input_dir=fmriprep_input_dir,LOGGER=LOGGER)

    pan_workflow.add_nodes([xcpd_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
