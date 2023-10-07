from panpipelines.utils.util_functions import *
from subprocess import run
import os
import glob


class panpipeline:

    def __init__(self, labels_dict,pipeline_dir, participant_label, name='template_panpipeline', createGraph=True, logging=None, execution={}):
        self.labels_dict = labels_dict
        self.pipeline_dir = pipeline_dir
        self.participant_label = participant_label
        self.name = name
        self.createGraph=createGraph
        self.execution = execution
        self.logging = logging


    def pre_run(self):
        pass

    def proc(self):
        pass

    def run(self):

        self.pre_run()
        if self.logging:
            self.logging.info(f"Running {self.name} pipeline")

        self.proc()

        self.post_run()

        results = self.get_results()
        if self.logging:
            self.logging.info(results)
        return results

    def post_run(self):
        pass

    def get_results(self):
        self.results = {}
        return self.results





