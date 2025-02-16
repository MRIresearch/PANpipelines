from nipype import Workflow, MapNode, Node
from nipype.interfaces.io import DataSink

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

    filecount_list=[]
    measures_list1=[]
    measures_template = getParams(labels_dict,"MEASURES_TEMPLATE")
    if isinstance(measures_template,list):
        for meas_template in measures_template:
            evaluated_meas_template = substitute_labels(meas_template,labels_dict)
            meas_files=glob.glob(evaluated_meas_template)
            measures_list1.extend(meas_files)
            filecount_list.append(len(meas_files))
    elif measures_template:
        measures_list1.extend(glob.glob(measures_template))


    collate_csv_node = collate_csv.create(labels_dict, csv_list1=measures_list1, LOGGER=LOGGER)


    sinker_dir = getParams(labels_dict,"SINKDIR")
    if sinker_dir:
        sinker = Node(DataSink(),name='collatecsv_sink')
        sinker_basedir = os.path.dirname(sinker_dir)
        sinker_folder = os.path.basename(sinker_dir)
        if not os.path.exists(sinker_basedir):
            os.makedirs(sinker_basedir,exist_ok=True)
        sinker.inputs.base_directory = sinker_basedir

        pan_workflow.connect( collate_csv_node,"roi_csv",sinker,f"{sinker_folder}")
        pan_workflow.connect( collate_csv_node,"roi_csv_metadata",sinker,f"{sinker_folder}.@metadata")

    else:
        pan_workflow.add_nodes([collate_csv_node])

    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
