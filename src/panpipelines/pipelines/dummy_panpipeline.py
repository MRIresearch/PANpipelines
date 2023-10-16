from panpipelines.utils.util_functions import *
from panpipelines.pipelines.panpipeline import *
import os
import glob
import panpipelines.workflows.dummy_workflow as panworkflow

class dummy_panpipeline(panpipeline):

    def __init__(self,labels_dict,pipeline_dir, participant_label,name='dummy_panpipeline',createGraph=True,logging=None,execution={}):

        super().__init__(labels_dict,pipeline_dir, participant_label,name,createGraph,logging,execution)

    def proc(self):
        workflow_dir = self.pipeline_dir
        workflow_name = "{}_wf".format(self.name)

        pan_workflow = panworkflow.create(workflow_name,workflow_dir,self.labels_dict,createGraph=self.createGraph,execution=self.execution)
        pan_workflow.run()
    
    def post_run(self):
        if self.logging:
            self.logging.info(f"Completed {self.name} pipeline for {self.participant_label}")

    def get_results(self):
        self.results = {}
        return self.results





