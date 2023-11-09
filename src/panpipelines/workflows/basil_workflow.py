from nipype import Workflow

import panpipelines.nodes.basil as basil
import panpipelines.nodes.fslanat as fslanat
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={}, LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    fslanat_node = fslanat.create(labels_dict,LOGGER=LOGGER)
    basil_node = basil.create(labels_dict,LOGGER=LOGGER)

    pan_workflow.connect(fslanat_node,'fslanat_dir',basil_node,'fslanat_dir')

    if createGraph:
         pan_workflow.write_graph(graph2use='flat')

    return pan_workflow
