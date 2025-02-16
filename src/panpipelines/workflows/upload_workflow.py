from nipype import Workflow,Node
from nipype.interfaces.io import DataSink

import panpipelines.nodes.upload as upload
from panpipelines.utils.util_functions import *


def create(name, wf_base_dir,labels_dict,createGraph=True,execution={},LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    source_path = getParams(labels_dict,"FTP_SOURCEPATH")
    source_list=[]
    if isinstance(source_path,list):
        for source_template in source_path:
            evaluated_source_template = substitute_labels(source_template,labels_dict)
            source_files=glob.glob(evaluated_source_template)
            source_list.extend(source_files)
    else:
        source_list=[source_path]

    remote_path = getParams(labels_dict,"FTP_REMOTEPATH")
    remote_list=[]
    if isinstance(remote_path,list):
        for remote_template in remote_path:
            evaluated_remote_template = substitute_labels(remote_template,labels_dict)
            remote_files=evaluated_remote_template
            remote_list.append(remote_files)
    else:
        remote_list=[remote_path]

    ftpcredentials = getParams(labels_dict,"FTPCREDENTIALS")

    upload_node = upload.create(labels_dict,source_list,remote_list, ftpcredentials,LOGGER=LOGGER)

    sinker_dir = getParams(labels_dict,"SINKDIR_GROUP")
    if sinker_dir:
        sinker = Node(DataSink(),name='collatecsvgroup_sink')
        sinker_basedir = os.path.dirname(sinker_dir)
        sinker_folder = os.path.basename(sinker_dir)
        if not os.path.exists(sinker_basedir):
            os.makedirs(sinker_basedir,exist_ok=True)
        sinker.inputs.base_directory = sinker_basedir

        pan_workflow.connect( upload_node,"metadata_file",sinker,f"{sinker_folder}.@metadata_file")
    else:
        pan_workflow.add_nodes([upload_node])


    if createGraph:
         pan_workflow.write_graph(graph2use='flat')


    return pan_workflow
