from nipype import Workflow, MapNode, Node

import panpipelines.nodes.antstransform as antstransform
import panpipelines.nodes.atlascreate as atlascreate
import panpipelines.nodes.roi_mean_single as roimean
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

    # do we need to create a custom atlas?
    atlas_index = getParams(labels_dict,"ATLAS_INDEX")
    atlas_file = getParams(labels_dict,"ATLAS_FILE")
    atlas_name = getParams(labels_dict,"ATLAS_NAME")
    atlascreate_node=None
    if not atlas_file:
        newatlas_list=[]
        newatlas_templates = getParams(labels_dict,"NEWATLAS_TEMPLATE")
        newatlas_index = getParams(labels_dict,"NEWATLAS_INDEX")
        if isinstance(newatlas_templates,list):
            for newatlas_template in newatlas_templates:
                evaluated_newatlas_template = substitute_labels(newatlas_template,labels_dict)
                if "*" not in evaluated_newatlas_template:
                    newatlas_list.append(evaluated_newatlas_template)
                else:
                    newatlas_list.extend(glob.glob(evaluated_newatlas_template))
        else:
            newatlas_list.extend(glob.glob(newatlas_templates))
            
        labels_dict = updateParams(labels_dict,"COST_FUNCTION","NearestNeighbor")
        labels_dict = updateParams(labels_dict,"OUTPUT_TYPE","int")
        atlascreate_node = atlascreate.create(labels_dict,name=f"atlascreate_{atlas_name}_node",roi_list=newatlas_list,roilabels_list=newatlas_index,LOGGER=LOGGER)

    roimean_node = roimean.create(labels_dict,name="subject_metrics",LOGGER=LOGGER)
    roimean_map_node = MapNode(roimean_node.interface,name="subject_metrics_map",iterfield=['input_file'])

    if atlascreate_node:
        pan_workflow.connect(atlascreate_node,'atlas_index',roimean_map_node,'atlas_index')
    else:
        roimean_map_node.inputs.atlas_index = atlas_index


    atlas_transform_mat=getParams(labels_dict,"ATLAS_TRANSFORM_MAT") 
    atlas_transform_ref=getParams(labels_dict,"ATLAS_TRANSFORM_REF")   
    # should we transform atlas?
    if atlas_transform_mat is not None:
        labels_dict = updateParams(labels_dict,"COST_FUNCTION","NearestNeighbor")
        labels_dict = updateParams(labels_dict,"OUTPUT_TYPE","int")
        if atlascreate_node:
            atlas_transform_node = antstransform.create(labels_dict,name="atlas_transform", trans_mat=atlas_transform_mat,ref_file=atlas_transform_ref, LOGGER=LOGGER)
            pan_workflow.connect(atlascreate_node,'atlas_file',atlas_transform_node,'input_file')    
        else:
            atlas_transform_node = antstransform.create(labels_dict,name="atlas_transform",input_file=atlas_file, trans_mat=atlas_transform_mat,ref_file=atlas_transform_ref, LOGGER=LOGGER)
        pan_workflow.connect(atlas_transform_node,'out_file',roimean_map_node,'atlas_file')
    else:
        if atlascreate_node:
            pan_workflow.connect(atlascreate_node,'atlas_file',roimean_map_node,'atlas_file') 
        else:
            roimean_map_node.inputs.atlas_file = atlas_file

    measures_list=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            measures_list.extend(glob.glob(evaluated_meas_template))
    else:
        measures_list.extend(glob.glob(measures_template))
        
    measures_list.sort()

    # should we transform measures?
    measures_transform_mat=getParams(labels_dict,"MEASURES_TRANSFORM_MAT")
    measures_transform_ref=getParams(labels_dict,"MEASURES_TRANSFORM_REF")
    if measures_transform_mat is not None:
        labels_dict = removeParam(labels_dict,"COST_FUNCTION")
        labels_dict = removeParam(labels_dict,"OUTPUT_TYPE")
        measures_transform_node = antstransform.create(labels_dict,name="measure_transform",trans_mat=measures_transform_mat,ref_file=measures_transform_ref,LOGGER=LOGGER)
        measures_transform_map_node = MapNode(measures_transform_node.interface,name="measure_transform_map",iterfield=['input_file'])
        measures_transform_map_node.inputs.input_file = measures_list
        pan_workflow.connect(measures_transform_map_node,'out_file',roimean_map_node,'input_file')
            
    else:
        pan_workflow.connect(measures_list,'out_file',roimean_map_node,'input_file')


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
