from panpipelines.utils.util_functions import *
from subprocess import run
import os
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

class panscript:

    def __init__(self,labels_dict,name='template_panscript',params="",command="",interactive=False, execution={}):

        # Create Node
        self.labels_dict = labels_dict
        self.name = name
        self.params = params
        self.command = command
        self.interactive = interactive


    def pre_run(self):
        pass

    def run(self):

        self.pre_run()

        IFLOGGER.info(f"Running PAN script - {self.name}")
        command=self.command + " " + self.params

        pkgdir = os.path.abspath(os.path.dirname(__file__))
        if getParams(self.labels_dict,"CHANGEDIR") == "N":
            IFLOGGER.info(f"Staying in current directory {os.getcwd()}to run script.")
        else:
            IFLOGGER.info(f"Changing to panscript directory {pkgdir} to execute.")
            os.chdir(pkgdir)
        
        evaluated_command=substitute_labels(command, self.labels_dict)
        runCommand(evaluated_command,IFLOGGER,interactive=self.interactive)

        self.post_run()
        return self.get_results()

    def post_run(self):
        pass

    def get_results(self):
        self.results = {}
        return self.results





