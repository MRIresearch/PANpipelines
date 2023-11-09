from panpipelines.utils.util_functions import *
from subprocess import run
import os
import glob


class panpipeline:

    def __init__(self, labels_dict,pipeline_dir, participant_label, name='template_panpipeline', createGraph=True, LOGGER=None, execution={}):
        self.labels_dict = labels_dict
        self.pipeline_dir = pipeline_dir
        self.participant_label = participant_label
        self.name = name
        self.createGraph=createGraph
        self.execution = execution
        self.LOGGER = LOGGER
        self.results={}


    def pre_run(self):
        if self.LOGGER:
            self.LOGGER.info(f"Running {self.name} pipeline")

    def proc(self):
        pass

    def run(self):

        self.pre_run()

        self.proc()

        self.post_run()

        results = self.get_results()
        if self.LOGGER:
            if results:
                self.LOGGER.info(results)
        return results

    def post_run(self):
        if self.LOGGER:
            self.LOGGER.info(f"Completed {self.name} pipeline for {self.participant_label}")

    def get_results(self):
        return self.results





