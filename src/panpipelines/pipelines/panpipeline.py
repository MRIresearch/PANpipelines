from panpipelines.utils.util_functions import *
from subprocess import run
import os
import glob


class panpipeline:

    def __init__(self, labels_dict,pipeline_dir, participant_label, name='template_panpipeline', createGraph=True, LOGGER=None, execution={},analysis_level="participant", participant_project=None):
        self.labels_dict = labels_dict
        self.pipeline_dir = pipeline_dir
        self.participant_label = participant_label
        self.name = name
        self.createGraph=createGraph
        self.execution = execution
        self.LOGGER = LOGGER
        self.analysis_level = analysis_level
        self.participant_project = participant_project
        self.results={}


    def pre_run(self):
        if self.LOGGER:
            self.LOGGER.info(f"Running {self.name} pipeline at {self.analysis_level} level")

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
            if self.analysis_level == "participant":
                if self.participant_project:
                    if self.LOGGER:
                        self.LOGGER.info(f"Completed {self.name} pipeline for {self.participant_label} in {self.participant_project}")
                else:
                    if self.LOGGER:
                        self.LOGGER.info(f"Completed {self.name} pipeline for {self.participant_label}")
            else:
                if self.participant_project:
                    if self.LOGGER:
                        participant_project_pairing = [ it for it in zip(self.participant_label,self.participant_project)]
                        self.LOGGER.info(f"Completed {self.name} pipeline at {self.analysis_level} level for:\n{participant_project_pairing}")             
                else:
                    if self.LOGGER:
                        self.LOGGER.info(f"Completed {self.name} pipeline at {self.analysis_level} level for:\n {self.participant_label}")

    def get_results(self):
        return self.results





