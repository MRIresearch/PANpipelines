from nipype import Workflow, MapNode, Node

import panpipelines.nodes.antstransform as antstransform
import panpipelines.nodes.parse_textdata as parse_textdata
from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import glob

def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)


    parsetextdata_node = parse_textdata.create(labels_dict,name="subject_text",LOGGER=LOGGER)
    parsetextdata_map_node = MapNode(parsetextdata_node.interface,name="subject_text_map",iterfield=['textdata'])

    measures_list=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            measures_list.extend(glob.glob(evaluated_meas_template))
    else:
        measures_list.extend(glob.glob(measures_template))
        
    measures_list.sort()

    parsetextdata_map_node.inputs.textdata = measures_list
    pan_workflow.add_nodes([parsetextdata_map_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
