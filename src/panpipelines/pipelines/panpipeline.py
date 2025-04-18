from panpipelines.utils.util_functions import *
from subprocess import run
import os
import glob


class panpipeline:

    def __init__(self, labels_dict,pipeline_dir, participant_label, name='template_panpipeline', createGraph=True, LOGGER=None, execution={},analysis_level="participant", participant_project=None, participant_session=None,panworkflow = None):
        self.labels_dict = labels_dict
        self.pipeline_dir = pipeline_dir
        self.participant_label = participant_label
        self.name = name
        self.createGraph=createGraph
        self.execution = execution
        self.LOGGER = LOGGER
        self.analysis_level = analysis_level
        self.participant_project = participant_project
        self.participant_session = participant_session
        self.panworkflow = panworkflow
        self.results={}


    def pre_run(self):
        log_message=f"Running {self.name} pipeline at {self.analysis_level} level for "
        if self.analysis_level == "participant":
            log_message = log_message + f"participant {self.participant_label} in "
            if self.participant_session:
                log_message = log_message + f"session {self.participant_session} in "
                if self.participant_project:
                    log_message = log_message + f"project {self.participant_project}\n"
        else:
            participant_info_pairing = [ it for it in zip(self.participant_label,self.participant_project, self.participant_session)]
            for part_info in participant_info_pairing:
                log_message = log_message + f"participant {part_info[0]} in "
                if part_info[1]:
                    log_message = log_message + f"session {part_info[1]} in "
                    if part_info[2]:
                        log_message = log_message + f"project {part_info[2]}\n" 
        if self.LOGGER:
            self.LOGGER.info(log_message)     

    def proc(self):
        workflow_dir = self.pipeline_dir
        workflow_name = "{}_wf".format(self.name)

        pan_workflow = self.panworkflow.create(workflow_name,workflow_dir,self.labels_dict,createGraph=self.createGraph,execution=self.execution, LOGGER=self.LOGGER)
        if isTrue(getParams(self.labels_dict,"FORCE_RUN")):
            MULTIPROC_NPROCS=getParams(self.labels_dict,"MULTIPROC_NPROCS")
            if MULTIPROC_NPROCS:
                MULTIPROC_NPROCS = int(MULTIPROC_NPROCS)
            else:
                MULTIPROC_NPROCS=1
            if self.LOGGER:
                self.LOGGER.info("Forced rerun of workflow selected ....")
            pan_workflow.run(plugin="MultiProc", plugin_args={"overwrite": True,'n_procs' : MULTIPROC_NPROCS})
        else:
            pan_workflow.run()

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
        log_message=f"Completed {self.name} pipeline at {self.analysis_level} level for "
        if self.analysis_level == "participant":
            log_message = log_message + f"participant {self.participant_label} in "
            if self.participant_session:
                log_message = log_message + f"session {self.participant_session} in "
                if self.participant_project:
                    log_message = log_message + f"project {self.participant_project} "
        else:
            participant_info_pairing = [ it for it in zip(self.participant_label,self.participant_project, self.participant_session)]
            for part_info in participant_info_pairing:
                log_message = log_message + f"participant {part_info[0]} in "
                if part_info[1]:
                    log_message = log_message + f"session {part_info[1]} in "
                    if part_info[2]:
                        log_message = log_message + f"project {part_info[2]} \n" 
        if self.LOGGER:
            self.LOGGER.info(log_message)          


    def get_results(self):
        return self.results





