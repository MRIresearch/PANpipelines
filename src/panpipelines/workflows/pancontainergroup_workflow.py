from nipype import Workflow, Node
from nipype.interfaces.io import DataSink

import panpipelines.nodes.pancontainergroup as pancontainergroup
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    pancontainergroup_node = pancontainergroup.create(labels_dict,LOGGER=LOGGER)

    sinker_dir = getParams(labels_dict,"SINKDIR_GROUP")
    if sinker_dir:
        sinker = Node(DataSink(),name='collatecsvgroup_sink')
        sinker_basedir = os.path.dirname(sinker_dir)
        sinker_folder = os.path.basename(sinker_dir)
        if not os.path.exists(sinker_basedir):
            os.makedirs(sinker_basedir,exist_ok=True)
        sinker.inputs.base_directory = sinker_basedir
        pan_workflow.connect( pancontainergroup_node,"output_file",sinker,f"{sinker_folder}.@output_file")
        pan_workflow.connect( pancontainergroup_node,"metadata_file",sinker,f"{sinker_folder}.@metadata_file")
    else:
        pan_workflow.add_nodes([pancontainergroup_node])
    
    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
