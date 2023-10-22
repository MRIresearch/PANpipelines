from panpipelines.pipelines import *
from panpipelines.scripts import *
import glob


class PANFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PANFactory, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        # Initialization logic for the factory (e.g., setting up resources)
        print("Initializing PANFactory.")
        self.pipelineDictionary = {}
        self.register_pipeline("aslprep_panpipeline",aslprep_panpipeline.aslprep_panpipeline)
        self.register_pipeline("basil_panpipeline",basil_panpipeline.basil_panpipeline)
        self.register_pipeline("dummy_panpipeline",dummy_panpipeline.dummy_panpipeline)
        self.register_pipeline("fmriprep_panpipeline",fmriprep_panpipeline.fmriprep_panpipeline)
        self.register_pipeline("freesurfer_panpipeline",freesurfer_panpipeline.freesurfer_panpipeline)
        self.register_pipeline("noddi_panpipeline",noddi_panpipeline.noddi_panpipeline)
        self.register_pipeline("panpipeline",panpipeline.panpipeline)
        self.register_pipeline("qsiprep_panpipeline",qsiprep_panpipeline.qsiprep_panpipeline)
        self.register_pipeline("tensor_panpipeline",tensor_panpipeline.tensor_panpipeline)
        self.register_pipeline("volmeasures_panpipeline",volmeasures_panpipeline.volmeasures_panpipeline)
        self.register_pipeline("textmeasures_panpipeline",textmeasures_panpipeline.textmeasures_panpipeline)
        self.register_pipeline("collatecsv_panpipeline",collatecsv_panpipeline.collatecsv_panpipeline)

        self.scriptDictionary = {}
        self.register_script("aslprep_panscript",aslprep_panscript.aslprep_panscript)
        self.register_script("fmriprep_panscript",fmriprep_panscript.fmriprep_panscript)
        self.register_script("panscript",panscript.panscript)

        print("PANFactory ready. Pipelines and scripts loaded.")
        print(f"Pipelines: {self.pipelineDictionary}")
        print(f"Scripts: {self.scriptDictionary}")

    def register_pipeline(self, name, pipeline):
        self.pipelineDictionary[name] = pipeline

    def get_pipeline(self, name):
        pipeline = self.pipelineDictionary.get(name)
        if not pipeline:
            raise ValueError(name)
        return pipeline

    def register_script(self, name, script):
        self.scriptDictionary[name] = script

    def get_script(self, name):
        script = self.scriptDictionary.get(name)
        if not script:
            raise ValueError(name)
        return script

    def get_processflow(self, name):
        if "script" in name:
            processflow = self.scriptDictionary.get(name)
        elif "pipeline" in name:
            processflow = self.pipelineDictionary.get(name)
        else:
            raise ValueError(name)
        if not processflow:
            raise ValueError(name)
        return processflow

def getPANFactory():
    return PANFactory()