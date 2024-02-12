from nipype import Workflow

import panpipelines.nodes.basil as basil
import panpipelines.nodes.fslanat as fslanat
from panpipelines.utils.util_functions import *
from bids import BIDSLayout
from sdcflows import fieldmaps as sfm
from nipype import Workflow, Node
from nipype.interfaces.io import DataSink
import panpipelines.scripts.pancontainer_panscript as pancontainer_script
import panpipelines.scripts.sdcflows_fieldmap as sdcflows_fieldmap

def create(name, wf_base_dir,labels_dict,createGraph=True,execution={}, LOGGER=None):
    # Create workflow
    pan_workflow = Workflow(name=name, base_dir=wf_base_dir)

    if LOGGER:
        LOGGER.info(f"Created Workflow {name} with base directory {wf_base_dir}")

    if len(execution.keys()) > 0:
        pan_workflow.config = process_dict(pan_workflow.config,execution)

    # Specify node inputs
    fslanat_manual=getParams(labels_dict,"FSLANAT_MANUAL")
    if fslanat_manual and fslanat_manual == "Y":
        fslanat_dir=getParams(labels_dict,"FSLANAT_DIR")
        basil_node = basil.create(labels_dict,fslanat_dir=fslanat_dir,LOGGER=LOGGER)
        pan_workflow.add_nodes([basil_node])
    else:
        fslanat_node = fslanat.create(labels_dict,LOGGER=LOGGER)
        basil_node = basil.create(labels_dict,LOGGER=LOGGER)
        pan_workflow.connect(fslanat_node,'fslanat_dir',basil_node,'fslanat_dir')

    FIELDMAP_TYPE = getParams(labels_dict,"FIELDMAP_TYPE")
    SDCFLOWS_FMAP_DIR = getParams(labels_dict,"SDCFLOWS_FIELDMAP_DIR")
    if FIELDMAP_TYPE and SDCFLOWS_FMAP_DIR:
        bids_dir = getParams(labels_dict,"BIDS_DIR")
        participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
        participant_session = getParams(labels_dict,'PARTICIPANT_SESSION')
        acq_label = getAcquisition(bids_dir,participant_label,participant_session=participant_session)
        if isinstance(FIELDMAP_TYPE,dict):
            if acq_label in FIELDMAP_TYPE.keys():
                FIELDMAP_TYPE = FIELDMAP_TYPE[acq_label]   

        if FIELDMAP_TYPE == "sdcflows_preproc":
            if isinstance(SDCFLOWS_FMAP_DIR,dict):
                if acq_label in SDCFLOWS_FMAP_DIR.keys():
                    SDCFLOWS_FMAP_DIR = SDCFLOWS_FMAP_DIR[acq_label]
                else:
                    SDCFLOWS_FMAP_DIR[acq_label]=substitute_labels("<WORKFLOW_DIR>/sdcflows/fmap",labels_dict) 
                    labels_dict = updateParams(labels_dict,"SDCFLOWS_FIELDMAP_DIR",SDCFLOWS_FMAP_DIR)
                    SDCFLOWS_FMAP_DIR = SDCFLOWS_FMAP_DIR[acq_label]

            # we have to mnanually substitute items from DICTs until we also check these in update_labels
            SDCFLOWS_FMAP_DIR=substitute_labels(SDCFLOWS_FMAP_DIR,labels_dict)
    
            SDCFLOWS_FMAP_MODE = getParams(labels_dict,"SDCFLOWS_FIELDMAP_MODE") 
            if SDCFLOWS_FMAP_MODE:
                sdcflows_fmap_mode = SDCFLOWS_FMAP_MODE
            else:
                sdcflows_fmap_mode="phasediff"
                labels_dict = updateParams(labels_dict,"SDCFLOWS_FIELDMAP_MODE",sdcflows_fmap_mode)
            
            sdcflows_workdir = os.path.dirname(SDCFLOWS_FMAP_DIR)
            if not os.path.exists(sdcflows_workdir):
                os.makedirs(sdcflows_workdir)

            sdcflows_fmap_parentdir = os.path.dirname(SDCFLOWS_FMAP_DIR)
            if not os.path.exists(sdcflows_fmap_parentdir):
                os.makedirs(sdcflows_fmap_parentdir)

            
            if sdcflows_fmap_mode == "phasediff":               
                sources = getPhaseDiffSources(bids_dir,participant_label,participant_session)
                sources_String = " ".join(sources)
                params = f"--fmap_sources {sources_String}" \
                    f" --subject {participant_label}" \
                    f" --session {participant_session}" \
                    f" --fieldmap_dir {SDCFLOWS_FMAP_DIR }" \
                    f" --workdir {sdcflows_workdir}"

            SDCFLOWS_CONTAINER_TO_USE = getParams(labels_dict,"SDCFLOWS_CONTAINER_TO_USE")
            if SDCFLOWS_CONTAINER_TO_USE:
                panscript = pancontainer_script.pancontainer_panscript(labels_dict,params=params,command=f"python {sdcflows_fieldmap.__file__}",container_img=SDCFLOWS_CONTAINER_TO_USE)
            else: 
                panscript = pancontainer_script.pancontainer_panscript(labels_dict,params=params,command=f"python {sdcflows_fieldmap.__file__}")
            panscript.run()

            
    if createGraph:
         pan_workflow.write_graph(graph2use='flat')

    return pan_workflow
