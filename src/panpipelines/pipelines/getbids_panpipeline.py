from panpipelines.utils.util_functions import *
from panpipelines.pipelines.panpipeline import *
import os
import glob
import panpipelines.workflows.getbids_workflow as panworkflow

TARGET_ANALYSIS_LEVEL=["participant","group"]

class getbids_panpipeline(panpipeline):

    def __init__(self,labels_dict,pipeline_dir, participant_label,name='getbids_panpipeline',createGraph=True,LOGGER=None,execution={},analysis_level="participant",participant_project=None,participant_session=None):

        if analysis_level not in TARGET_ANALYSIS_LEVEL:
            if LOGGER:
                LOGGER.error(f"pipeline {name} not defined for {analysis_level}")
                raise ValueError(f"pipeline {name} not defined for {analysis_level}")

        super().__init__(labels_dict,pipeline_dir, participant_label,name,createGraph,LOGGER,execution,analysis_level, participant_project,participant_session,panworkflow)





