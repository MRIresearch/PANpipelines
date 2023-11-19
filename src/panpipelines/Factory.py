from panpipelines.pipelines import *
from panpipelines.scripts import *
import glob
import logging
from panpipelines.utils.util_functions import logger_setup

LOGGER = logger_setup("panpipelines.single_subject", logging.DEBUG)

class PANFactory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PANFactory, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        # Initialization logic for the factory (e.g., setting up resources)
        LOGGER.debug("Initializing PANFactory.")
        root_module = "panpipelines"
        self.pipeline_module = f"{root_module}.pipelines"
        self.script_module = f"{root_module}.scripts"
        self.workflow_module = f"{root_module}.workflows"
        self.node_module = f"{root_module}.nodes"
        self.atlas_module = f"{root_module}.atlases"
        self.transform_module = f"{root_module}.transforms"

        LOGGER.debug("PANFactory ready. Modules defined.")
        LOGGER.debug(f"Pipelines: {self.pipeline_module}")
        LOGGER.debug(f"Scripts: {self.script_module}")
        LOGGER.debug(f"Workflows: {self.workflow_module}")
        LOGGER.debug(f"Nodes: {self.node_module}")
        LOGGER.debug(f"Transforms: {self.transform_module}")
        LOGGER.debug(f"Atlases: {self.atlas_module}")

    def get_node(self, name):

        try:
            # currently node and worfklow not defined as classes
            module = __import__(f"{self.node_module}.{name}",fromlist=[name])
            if module:
                return module
            else:
                return None
        except Exception as ex:
            pass

    def get_workflow(self, name):

        try:
            # currently node and worfklow not defined as classes
            module = __import__(f"{self.workflow_module}.{name}",fromlist=[name])
            if module:
                return module
            else:
                return None
        except Exception as ex:
            pass


    def get_atlas(self, name):
        try:
            module = __import__(f"{self.atlas_module}.{name}",fromlist=[name])
            if hasattr(module,name):
                atlasclass = getattr(module,name)
                return atlasclass
            else:
                return None
        except Exception as ex:
            pass

    def get_transform(self, name):
        try:
            module = __import__(f"{self.transform_module}.{name}",fromlist=[name])
            if hasattr(module,name):
                transformclass = getattr(module,name)
                return transformclass
            else:
                return None
        except Exception as ex:
            pass


    def get_pipeline(self, name):

        try:
            module = __import__(f"{self.pipeline_module}.{name}",fromlist=[name])
            if hasattr(module,name):
                pipeclass = getattr(module,name)
                return pipeclass
            else:
                raise None
        except Exception as ex:
            pass

    def get_script(self, name):
        try:
            module = __import__(f"{self.script_module}.{name}",fromlist=[name])
            if hasattr(module,name):
                scriptclass = getattr(module,name)
                return scriptclass
            else:
                return None
        except Exception as ex:
            pass

    def get_processflow(self, name):
        if "script" in name:
            processflow = self.get_script(name)
        elif "pipeline" in name:
            processflow = self.get_pipeline(name)           
        elif "workflow" in name:
            processflow = self.get_workflow(name)
        else:
            processflow = self.get_node(name)

        if not processflow:
            LOGGER.error(f"PAN object {name} not defined.")
            raise ValueError(f"{name} cannot be resolved as a PAN object by Factory")

        LOGGER.debug(f"PANfactory retrieving {processflow}")
        return processflow

    def get_PANclass(self, name):
        if "atlas" in name:
            panclass = self.get_atlas(name)
        elif "transform" in name:
            panclass = self.get_transform(name)
        else:
            panclass = self.get_processflow(name)

        if not panclass:
            raise ValueError(name)

        LOGGER.debug(f"PANfactory retrieving {panclass}")
        return panclass


    def search_PANclass(self, name):

        panclass = self.get_transform(name)

        if not panclass:
            panclass = self.get_atlas(name)

        if not panclass:
            panclass = self.get_pipeline(name)

        if not panclass:
            panclass = self.get_script(name)

        if not panclass:
            panclass = self.get_node(name)

        if not panclass:
            panclass = self.get_workflow(name)

        if not panclass:
            raise ValueError(name)

        LOGGER.debug(f"PANfactory retrieving {panclass}")
        return panclass

def getPANFactory():
    return PANFactory()