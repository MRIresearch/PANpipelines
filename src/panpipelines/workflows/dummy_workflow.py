from nipype import Workflow

import panpipelines.nodes.dummy as dummy
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={}):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    dummy_node = dummy.create(labels_dict)

    pan_workflow.add_nodes([dummy_node])

    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
