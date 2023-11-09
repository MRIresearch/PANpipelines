from panpipelines.utils.util_functions import *
from panpipelines.pipelines.panpipeline import *
import os
import glob
import panpipelines.workflows.noddi_workflow as panworkflow

class noddi_panpipeline(panpipeline):

    def __init__(self,labels_dict,pipeline_dir, participant_label, name='noddi_panpipeline',createGraph=True,LOGGER=None,execution={}):

        super().__init__(labels_dict,pipeline_dir, participant_label,name,createGraph,LOGGER,execution)

    def proc(self):
        workflow_dir = self.pipeline_dir
        workflow_name = "{}_wf".format(self.name)

        pan_workflow = panworkflow.create(workflow_name,workflow_dir,self.labels_dict,createGraph=self.createGraph,execution=self.execution, LOGGER=self.LOGGER)
        pan_workflow.run()





