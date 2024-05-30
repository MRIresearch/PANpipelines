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
    parsetextdata_map_node = MapNode(parsetextdata_node.interface,name="subject_text_map",iterfield=['textdata','textdata_type','custom_prefix'])

    filecount_list=[]
    measures_list=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            meas_files=glob.glob(evaluated_meas_template)
            measures_list.extend(meas_files)
            filecount_list.append(len(meas_files))
    else:
        measures_list.extend(glob.glob(measures_template))
    measures_len = len(measures_list)

    measures_texttype_list=["" for x in range(measures_len)]
    measures_texttypes = getParams(labels_dict,"MEASURES_TEXTTYPES")
    file_index=0
    for meas_file in measures_list:
        if measures_texttypes and isinstance(measures_texttypes,dict):
            for itemkey, itemvalue in measures_texttypes.items():
                if substitute_labels(itemkey,labels_dict) in os.path.basename(meas_file):
                    measures_texttype_list[file_index] =substitute_labels(itemvalue,labels_dict)
                    break
        file_index=file_index + 1


    measures_prefix_list=["" for x in range(measures_len)]
    measures_prefixes = getParams(labels_dict,"MEASURES_PREFIXES")
    file_index=0
    for meas_file in measures_list:
        if measures_prefixes and isinstance(measures_prefixes,dict):
            for itemkey, itemvalue in measures_prefixes.items():
                if substitute_labels(itemkey,labels_dict) in os.path.basename(meas_file):
                    measures_prefix_list[file_index] = substitute_labels(itemvalue,labels_dict)
                    break
        file_index=file_index + 1

    parsetextdata_map_node.inputs.textdata = measures_list
    parsetextdata_map_node.inputs.textdata_type = measures_texttype_list
    parsetextdata_map_node.inputs.custom_prefix = measures_prefix_list
    pan_workflow.add_nodes([parsetextdata_map_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
