from nipype import Workflow, MapNode, Node
from nipype.interfaces.io import DataSink

import panpipelines.nodes.antstransform as antstransform
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

    transform_node = antstransform.create(labels_dict,name="subject_transform",LOGGER=LOGGER)
    transform_map_node = MapNode(transform_node.interface,name="subject_transform_map",iterfield=['input_file'])

    transform_mat=getParams(labels_dict,"TRANSFORM_MAT") 
    transform_ref=getParams(labels_dict,"TRANSFORM_REF")

    transform_map_node.inputs.trans_mat = transform_mat
    transform_map_node.inputs.ref_file = transform_ref


    moving_list=[]
    moving_template = getParams(labels_dict,"MOVING_FILES")
    if isinstance(moving_template,list):
        for meas_template in moving_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            moving_list.extend(glob.glob(evaluated_meas_template))
    else:
        evaluated_moving_template = substitute_labels(moving_template,labels_dict)
        moving_list.extend(glob.glob(evaluated_moving_template))
        
    moving_list.sort()
    if LOGGER:
        LOGGER.info(f"Moving files evaluated as: {moving_list}")
    if moving_list:
        transform_map_node.inputs.input_file = moving_list
    else:
        if LOGGER:
            LOGGER.warn(f"Something went wrong. Should not have empty list of moving files. Stopping.")
        sys.exit(1)

    pan_workflow.add_nodes([transform_map_node])

    sinker_dir = getParams(labels_dict,"TRANSFORMDIR")
    if sinker_dir:
        sinker = Node(DataSink(),name='transform_sink')
        sinker_basedir = os.path.dirname(sinker_dir)
        sinker_folder = os.path.basename(sinker_dir)
        if not os.path.exists(sinker_basedir):
            os.makedirs(sinker_basedir,exist_ok=True)
        sinker.inputs.base_directory = sinker_basedir

        measure_count=0
        substitutions=[]
        for measure_name in moving_list:
            measure_name_parts = os.path.basename(measure_name).split("_")
            if len(measure_name_parts) > 1:
                measure_name_stub = "_".join(measure_name_parts[-2:])
            else:
                measure_name_stub = measure_name_parts[-1]

            measure_name_suffix = measure_name_stub.split(".")[0]
            substitutions+=[("_subject_transform_map" +str(measure_count),measure_name_suffix)]
            measure_count = measure_count + 1 
        if substitutions:
            sinker.inputs.substitutions = substitutions

        pan_workflow.connect( transform_map_node,"out_file",sinker,f"{sinker_folder}")
        
    if createGraph:
         pan_workflow.write_graph(graph2use='flat')

    return pan_workflow
