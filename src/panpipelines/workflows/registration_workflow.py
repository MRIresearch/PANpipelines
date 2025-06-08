from nipype import Workflow, MapNode, Node
from nipype.interfaces.io import DataSink

import panpipelines.nodes.registration as registration
from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import glob
import sys

def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    moving=getGlob(substitute_labels(getParams(labels_dict,"MOVING"),labels_dict))
    reference=getGlob(substitute_labels(getParams(labels_dict,"REFERENCE"),labels_dict))
    registration_type=getParams(labels_dict,"REGISTRATION_TYPE")

    registration_node = registration.create(labels_dict,name="subject_register",input_file=moving, ref_file=reference, registration_type=registration_type, LOGGER=LOGGER)

    pan_workflow.add_nodes([registration_node])

    if createGraph:
         pan_workflow.write_graph(graph2use='flat')

    return pan_workflow
