from nipype import Workflow, MapNode, Node

import panpipelines.nodes.antstransform as antstransform
import panpipelines.nodes.atlascreate as atlascreate
import panpipelines.nodes.roi_extract as roiextract
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

    # do we have  a mask to exclude?
    maskcreate_node = None
    mask_templates = getParams(labels_dict,"MASK_TEMPLATE")
    if mask_templates:
        mask_list=[]
        mask_name = getParams(labels_dict,"MASK_NAME")
        if not mask_name:
            mask_name="mask"
        mask_index = getParams(labels_dict,"MASK_INDEX")
        if isinstance(mask_templates,list):
            for mask_template in mask_templates:
                evaluated_mask_template = substitute_labels(mask_template,labels_dict)
                if "*" not in evaluated_mask_template:
                    mask_list.append(evaluated_mask_template)
                else:
                    mask_list.extend(glob.glob(evaluated_mask_template))
        else:
            mask_list.extend(glob.glob(mask_templates))

        # if mask template is invalid then continue, otherwise print message and continue without
        # using mask segmenntation
        MASK_TEMPLATE_EXISTS=True
        for mask in mask_list:
            if not os.path.exists(mask):
                MASK_TEMPLATE_EXISTS = False

        if mask_list and MASK_TEMPLATE_EXISTS and getParams(labels_dict,"MASK_TRANSFORM_MAT"):    
            # store and restore parameters used by both mask and newatlas
            newatlas_transform_mat = getParams(labels_dict,"NEWATLAS_TRANSFORM_MAT")
            newatlas_transform_ref = getParams(labels_dict,"NEWATLAS_TRANSFORM_REF")
            newatlas_type = getParams(labels_dict,"NEWATLAS_TYPE")
            newatlas_name = getParams(labels_dict,"NEWATLAS_NAME")
            newatlas_probthresh = getParams(labels_dict,"NEWATLAS_PROBTHRESH")
            newatlas_invertroi = getParams(labels_dict,"NEWATLAS_INVERTROI")
            newatlas_indexmode = getParams(labels_dict,"NEWATLAS_INDEXMODE")

            mask_transform_mat = getParams(labels_dict,"MASK_TRANSFORM_MAT")
            mask_transform_ref = getParams(labels_dict,"MASK_TRANSFORM_REF")
            mask_type = getParams(labels_dict,"MASK_TYPE")
            if not mask_type:
                mask_type = "3D_mask"
            mask_name = getParams(labels_dict,"MASK_NAME")
            mask_probthresh = getParams(labels_dict,"MASK_PROBTHRESH")
            mask_invertroi = getParams(labels_dict,"MASK_INVERTROI")
            mask_indexmode = getParams(labels_dict,"MASK_INDEXMODE")

            labels_dict = updateParams(labels_dict,"NEWATLAS_TRANSFORM_MAT",mask_transform_mat)
            labels_dict = updateParams(labels_dict,"NEWATLAS_TRANSFORM_REF",mask_transform_ref)
            labels_dict = updateParams(labels_dict,"NEWATLAS_TYPE",mask_type)
            labels_dict = updateParams(labels_dict,"NEWATLAS_NAME",mask_name)
            labels_dict = updateParams(labels_dict,"NEWATLAS_PROBTHRESH",mask_probthresh)
            labels_dict = updateParams(labels_dict,"NEWATLAS_INVERTROI",mask_invertroi)
            labels_dict = updateParams(labels_dict,"NEWATLAS_INDEXMODE",mask_indexmode)

            labels_dict = updateParams(labels_dict,"COST_FUNCTION","NearestNeighbor")
            maskcreate_node = atlascreate.create(labels_dict,name=f"maskcreate_{mask_name}_node",roi_list=mask_list,roilabels_list=mask_index,LOGGER=LOGGER)

            labels_dict = updateParams(labels_dict,"NEWATLAS_TRANSFORM_MAT",newatlas_transform_mat)
            labels_dict = updateParams(labels_dict,"NEWATLAS_TRANSFORM_REF",newatlas_transform_ref)
            labels_dict = updateParams(labels_dict,"NEWATLAS_TYPE",newatlas_type)
            labels_dict = updateParams(labels_dict,"NEWATLAS_NAME",newatlas_name)
            labels_dict = updateParams(labels_dict,"NEWATLAS_PROBTHRESH",newatlas_probthresh)
            labels_dict = updateParams(labels_dict,"NEWATLAS_INVERTROI",newatlas_invertroi)
            labels_dict = updateParams(labels_dict,"NEWATLAS_INDEXMODE",newatlas_indexmode)
        else:
            if LOGGER:
                LOGGER.info(f"mask Template defined but valid template file not found. Ignoring mask Template.")

    # do we need to create a custom atlas?
    atlas_index = getParams(labels_dict,"ATLAS_INDEX")
    atlas_file = getParams(labels_dict,"ATLAS_FILE")
    atlas_name = getParams(labels_dict,"ATLAS_NAME")
    atlascreate_node=None
    if not atlas_file:
        newatlas_list=[]
        newatlas_templates = getParams(labels_dict,"NEWATLAS_TEMPLATE")
        newatlas_index = getParams(labels_dict,"NEWATLAS_INDEX")
        if not atlas_name:
            atlas_name = getParams(labels_dict,"NEWATLAS_NAME")
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
        atlascreate_node = atlascreate.create(labels_dict,name=f"atlascreate_{atlas_name}_node",roi_list=newatlas_list,roilabels_list=newatlas_index,LOGGER=LOGGER)

    roimean_node = roiextract.create(labels_dict,name="subject_metrics",LOGGER=LOGGER)
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
        evaluated_measures_template = substitute_labels(measures_template,labels_dict)
        measures_list.extend(glob.glob(evaluated_measures_template))
        
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
        roimean_map_node.inputs.input_file = measures_list


    if maskcreate_node:
        pan_workflow.connect(maskcreate_node,'atlas_file',roimean_map_node,'mask_file')
    elif mask_templates:
        roimean_map_node.inputs.mask_file = mask_templates



    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
