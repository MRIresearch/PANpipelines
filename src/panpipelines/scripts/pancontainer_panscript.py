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

        PKG_DIR = getParams(labels_dict,"PKG_DIR")
        os.environ["PYTHONPATH"]=f"{PKG_DIR}:$PYTHONPATH"
        os.environ["SINGULARITYENV_PYTHONPATH"]=translate_binding(command_base,f"{PKG_DIR}:$PYTHONPATH")

        self.command = command_base + " " + command







