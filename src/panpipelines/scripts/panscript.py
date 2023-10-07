from panpipelines.utils.util_functions import *
from subprocess import run
import os
import glob

# TEST
#from panpipelines.scripts.panscript import *
#command="<COMM>"
#labels_dict={"COMM": "ls"}
#params="./"
#pancomm = panscript(labels_dict, params=params,command=command)
#pancomm.run()

class panscript:

    def __init__(self,labels_dict,name='template_panscript',params="",command="",execution={}):

        # Create Node
        self.labels_dict = labels_dict
        self.name = name
        self.params = params
        self.command = command


    def pre_run(self):
        pass

    def run(self):

        self.pre_run()

        print("Running PAN script")
        script_command=self.command + " " + self.params
        print(f"{script_command}")
        evaluated_command=substitute_labels(script_command, self.labels_dict)
        print(f"{evaluated_command}")

        process = run(evaluated_command.split(), capture_output=True)
        print(process.stdout.decode())

        self.post_run()
        return self.get_results()

    def post_run(self):
        pass

    def get_results(self):
        self.results = {}
        return self.results





