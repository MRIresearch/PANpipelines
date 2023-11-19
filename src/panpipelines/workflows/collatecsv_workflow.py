from nipype import Workflow, MapNode, Node

import panpipelines.nodes.antstransform as antstransform
import panpipelines.nodes.collate_csv_single as collate_csv
from panpipelines.utils.util_functions import *
from panpipelines.utils.transformer import *
import glob

def create(name, wf_base_dir,labels_dict,createGraph=True,execution={}, LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    measures_list1=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE1")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            measures_list1.extend(glob.glob(evaluated_meas_template))
    elif measures_template:
        measures_list1.extend(glob.glob(measures_template))

    measures_list1.sort()

    measures_list2=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE2")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            measures_list2.extend(glob.glob(evaluated_meas_template))
    elif measures_list2:
        measures_list2.extend(glob.glob(measures_template))

    measures_list2.sort()

    collate_csv_node = collate_csv.create(labels_dict, csv_list1=measures_list1, csv_list2=measures_list2, LOGGER=LOGGER)
    pan_workflow.add_nodes([collate_csv_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
