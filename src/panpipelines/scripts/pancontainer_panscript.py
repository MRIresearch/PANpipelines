from panpipelines.utils.util_functions import *
from panpipelines.scripts.panscript import *
import datetime


class pancontainer_panscript(panscript):

    def __init__(self,labels_dict,name='pancontainer_panscript',params="",command="",interactive=False,container_img="PAN_CONTAINER",execution={}):
        super().__init__(labels_dict,name=name,params=params,command=command,interactive=interactive)

        self.params = params

        if not container_img:
            container_img = "PAN_CONTAINER"

        command_base, container = getContainer(labels_dict,nodename="pancontainer_panscript",SPECIFIC=container_img,LOGGER=IFLOGGER)

        if container:
            IFLOGGER.info("\nChecking the container version:")
            version_command = f"{command_base} --version"
            evaluated_command=substitute_labels(version_command, labels_dict)
            runCommand(evaluated_command,IFLOGGER)

        PAN_PKG_DIR = getParams(labels_dict,"PAN_PKG_DIR")

        ADD_PKG_DIR = getParams(labels_dict,"ADD_PKG_DIR")
        if not isTrue(ADD_PKG_DIR):
            PAN_PKG_DIR=""

        EXTRA_PKG_DIR = getParams(labels_dict,"EXTRA_PKG_DIR")
        if EXTRA_PKG_DIR:
            EXTRA_PKG_DIR = f":{EXTRA_PKG_DIR}"
        else:
            EXTRA_PKG_DIR = ""

        if "PYTHONPATH" in os.environ.keys():
            PYTHONPATH = os.environ["PYTHONPATH"]
            PYTHONPATH = f":{PYTHONPATH}"
        else:
            PYTHONPATH = ""

        OVERRIDE_PYTHON_PATH = getParams(labels_dict,"OVERRIDE_PYTHON_PATH")
        if OVERRIDE_PYTHON_PATH:
            NEW_PYTHONPATH = f":{OVERRIDE_PYTHON_PATH}"
        else:
            NEW_PYTHONPATH  = f"{PAN_PKG_DIR}{PYTHONPATH}{EXTRA_PKG_DIR}"       
            
        os.environ["PYTHONPATH"]=NEW_PYTHONPATH
        os.environ["SINGULARITYENV_PYTHONPATH"]=translate_binding(command_base,f"{NEW_PYTHONPATH}")

        self.command = command_base + " " + command







