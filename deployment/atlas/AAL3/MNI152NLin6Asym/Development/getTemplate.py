import json
from shutil import copyfile
from pathlib import Path
from functools import partial
import os

def _path_exists(path, parser):
    """Ensure a given path exists."""
    if path is None or not Path(path).exists():
        raise parser.error(f"Path does not exist: <{path}>.")
    return Path(path).expanduser().absolute()

def get_parser():
    from argparse import ArgumentParser
    from argparse import RawTextHelpFormatter

    parser = ArgumentParser(description="Get Templare from template flow.")
    PathExists = partial(_path_exists, parser=parser)
    parser.add_argument("TemplateFlowDir", type=PathExists, help="The directory where templatefiles will be stored")
    parser.add_argument('--template_dict', action='store',type=json.loads,
        help='Template parameters as json dictionary.')

    return parser


def getTemplateRef(TEMPLATEFLOW_HOME,template_space,suffix=None,desc=None,resolution=None,extension=[".nii.gz"]):
    os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

    from templateflow import api as tf

    template_ref=tf.get(template_space,resolution=resolution,desc=desc,suffix=suffix,extension=extension)
    return template_ref


def main():

    opts = get_parser().parse_args()

    template_dict = None
    if opts.template_dict:
        template_dict = opts.template_dict

    template= "MNI152NLin6Asym"
    if "template" in template_dict:
        template = template_dict["template"]

    suffix = None
    if "suffix" in template_dict:
        suffix = template_dict["suffix"]

    desc = None
    if "desc" in template_dict:
        desc = template_dict["desc"]

    resolution = None
    if "resolution" in template_dict:
        resolution = template_dict["resolution"]

    extension = [".nii.gz"]
    if "extension" in template_dict:
        extension = template_dict["extension"]

    templateRef = getTemplateRef(str(opts.TemplateFlowDir),template,suffix=suffix,desc=desc,resolution=resolution,extension=extension)
    templateCurr = os.path.join(os.getcwd(),os.path.basename(templateRef))
    copyfile(templateRef,templateCurr)



# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
    main()
