from nipype import Workflow, MapNode, Node
from nipype.interfaces.io import DataSink

import panpipelines.nodes.antstransform as antstransform
import panpipelines.nodes.collate_csv_group as collate_csv_group
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

    # we will not evaluate these variables now as we will need them to be evaluated later in the node
    EXCEPTIONS=["PARTICIPANT_LABEL","PARTICIPANT_XNAT_RPOJECT","PARTICIPANT_SESSION"]

    measures_list1=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE1")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict, EXCEPTIONS)
            measures_list1.extend([evaluated_meas_template])
    elif measures_template:
        measures_list1.extend([substitute_labels(meas_template,labels_dict, EXCEPTIONS)])

    measures_list2=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE2")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict, EXCEPTIONS)
            measures_list2.extend([evaluated_meas_template])
    elif measures_list2:
        measures_list2.extend([substitute_labels(meas_template,labels_dict, EXCEPTIONS)])

    sinker_dir = getParams(labels_dict,"SINKDIR_GROUP")
    if sinker_dir:
        last_output_files = glob.glob(os.path.join(sinker_dir,"*"))
        if last_output_files:
            labels_dict = updateParams(labels_dict,"LAST_OUTPUT_FILES",last_output_files)

    collate_csv_groupnode = collate_csv_group.create(labels_dict, csv_list1=measures_list1, csv_list2=measures_list2, LOGGER=LOGGER)

    if sinker_dir:
        sinker = Node(DataSink(),name='collatecsvgroup_sink')
        sinker_basedir = os.path.dirname(sinker_dir)
        sinker_folder = os.path.basename(sinker_dir)
        if not os.path.exists(sinker_basedir):
            os.makedirs(sinker_basedir,exist_ok=True)
        sinker.inputs.base_directory = sinker_basedir

        pan_workflow.connect( collate_csv_groupnode,"roi_csv_inner",sinker,f"{sinker_folder}.@inner")
        pan_workflow.connect( collate_csv_groupnode,"roi_csv_inner_metadata",sinker,f"{sinker_folder}.@inner_metadata")
        pan_workflow.connect( collate_csv_groupnode,"roi_csv_outer",sinker,f"{sinker_folder}.@outer")
        pan_workflow.connect( collate_csv_groupnode,"roi_csv_outer_metadata",sinker,f"{sinker_folder}.@outer_metadata")
    else:
        pan_workflow.add_nodes([collate_csv_groupnode])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
