from panpipelines.utils.util_functions import *
from panpipelines.pipelines.panpipeline import *
import os
import glob
import panpipelines.workflows.collatecsvgroup_workflow as panworkflow

TARGET_ANALYSIS_LEVEL=["group"]

class collatecsvgroup_panpipeline(panpipeline):

    def __init__(self,labels_dict,pipeline_dir, participant_label, name='collatecsvgroup_panpipeline',createGraph=True,LOGGER=None,execution={},analysis_level = "group", participant_project=None):

        # perhaps check here that the analysis_level is indeed group!
        if analysis_level not in TARGET_ANALYSIS_LEVEL:
            if LOGGER:
                LOGGER.error(f"pipeline {name} not defined for {analysis_level}")
                raise ValueError(f"pipeline {name} not defined for {analysis_level}")

        super().__init__(labels_dict,pipeline_dir, participant_label,name,createGraph,LOGGER,execution,analysis_level, participant_project)

    def proc(self):
        workflow_dir = self.pipeline_dir
        workflow_name = "{}_wf".format(self.name)

        pan_workflow = panworkflow.create(workflow_name,workflow_dir,self.labels_dict,createGraph=self.createGraph,execution=self.execution,LOGGER=self.LOGGER)
        pan_workflow.run()




