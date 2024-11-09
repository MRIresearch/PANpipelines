from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import shlex
import subprocess
from nipype import logging as nlogging
import panpipelines.scripts.pancontainer_panscript as pancontainer_script
from panpipelines import Factory

IFLOGGER=nlogging.getLogger('nipype.interface')


def pancontainergroup_proc(labels_dict):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)

    datelabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    labels_dict = updateParams(labels_dict,"DATELABEL",datelabel)

    pipeline_config_loc= getParams(labels_dict,"PIPELINE_CONFIG_LOC")
    if not pipeline_config_loc:
        pipeline_config_loc = f"<CWD>/pipeline_config_file_{datelabel}.config"
        labels_dict = updateParams(labels_dict,"PIPELINE_CONFIG_LOC",pipeline_config_loc)

    pipeline_config_loc = substitute_labels(f"{pipeline_config_loc}",labels_dict)
    export_labels(labels_dict,pipeline_config_loc)

    panFactory = Factory.getPANFactory()
    script_class= getParams(labels_dict,"SCRIPT_CLASS")
    script_file= getParams(labels_dict,"SCRIPT_FILE")
    if script_file:       
        new_script_file = newfile(assocfile=script_file,prefix="pantransformed")
        with open(script_file,"r") as infile:
            script_lines = infile.readlines()

        new_script_lines =[]
        for x in script_lines:
            new_script_lines.append(special_substitute_labels(x,labels_dict))

        with open(new_script_file,"w") as outfile:
            outfile.writelines(new_script_lines)

        script_file = new_script_file

    elif script_class:
        run_script = panFactory.get_runscript(script_class)
        script_file = run_script.__file__

    elif LOGGER:
        LOGGER.warn(f"<SCRIPT_CLASS> and <SCRIPT_FILE> not defined. Cannot proceed")
        sys.exit(1)
    else:
        print(f"<SCRIPT_CLASS> and <SCRIPT_FILE> not defined. Cannot proceed")
        sys.exit(1)       


    # Specify script inputs
    params = special_substitute_labels(getParams(labels_dict,"PANCONTAINER_PARAMS"),labels_dict)
    main_command = special_substitute_labels(getParams(labels_dict,"PANCONTAINER_COMMANDS"),labels_dict)
    if not main_command:
        main_command = "python"

    CONTAINER_TO_USE = getParams(labels_dict,"CONTAINER_TO_USE")
    script_interactive= isTrue(getParams(labels_dict,"SCRIPT_INTERACTIVE"))
    try:
        if CONTAINER_TO_USE:
            panscript = pancontainer_script.pancontainer_panscript(labels_dict,params=params,command=f"{main_command} {script_file}",interactive=script_interactive, container_img=CONTAINER_TO_USE)
        else: 
            panscript = pancontainer_script.pancontainer_panscript(labels_dict,params=params,interactive=script_interactive,command=f"{main_command} {script_file}")
        panscript.run()
    except Exception as e:
        IFLOGGER.error(f"Exception thrown by {script_file} script {e}")


    with open(pipeline_config_loc,"r") as infile:
        pipeline_config_json = json.load(infile)

    if pipeline_config_json and "METADATA_FILE" in pipeline_config_json.keys():
        metadata_file = pipeline_config_json["METADATA_FILE"]
    elif "METADATA_FILE" in labels_dict:
        metadata_file = labels_dict["METADATA_FILE"]
    else:
        metadata_file = os.path.join(cwd,f'{os.path.basename(script_file)}_metadata.json')
        with open(metadata_file,"w") as outfile:
            outfile.write(f"No metadata file created by script")

    if pipeline_config_json and "OUTPUT_FILE" in pipeline_config_json.keys():
        output_file = pipeline_config_json["OUTPUT_FILE"]
    elif "OUTPUT_FILE" in labels_dict:
        output_file = labels_dict["OUTPUT_FILE"]
    else:
        output_file = os.path.join(cwd,f'{os.path.basename(script_file)}_output.json')
        with open(output_file,"w") as outfile:
            outfile.write(f"No output file created by script")
    
    out_files=[]
    out_files.insert(0,output_file)
    out_files.insert(1,metadata_file)
    out_files.insert(2,script_file)
    out_files.insert(3,pipeline_config_loc)

    return {
        "output_file" : output_file,
        "metadata_file" : metadata_file,
        "pipeline_config" :pipeline_config_loc,
        "out_files":out_files
    }


class pancontainergroupInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)

class pancontainergroupOutputSpec(TraitedSpec):
    output_file = File(desc='output file for upload')
    metadata_file = File(desc='metadata file for upload')
    pipeline_config = File(desc='pipeline_config')
    out_files = traits.List(desc='list of files')
    
class pancontainergroup_pan(BaseInterface):
    input_spec = pancontainergroupInputSpec
    output_spec = pancontainergroupOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = pancontainergroup_proc(
            self.inputs.labels_dict,
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name='pancontainergroup_node', LOGGER=IFLOGGER):
    # Create Node
    pan_node = Node(pancontainergroup_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")

    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    
    return pan_node


