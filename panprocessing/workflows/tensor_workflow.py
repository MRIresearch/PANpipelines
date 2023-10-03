from nipype import Workflow

import panprocessing.nodes.tensor as tensor
from panprocessing.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={}):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    qsiprep_input_dir = getParams(labels_dict,"QSIPREP_OUTPUT_DIR")
    tensor_node = tensor.create(labels_dict, input_dir=qsiprep_input_dir)

    pan_workflow.add_nodes([tensor_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow