from panpipelines.utils.util_functions import *
from panpipelines.scripts.panscript import *
import os
import glob

# TEST
#from panpipelines.scripts import *
#SCRIPT="fmriprep_panscript"
#panscript=eval("{}.{}".format(SCRIPT,SCRIPT))
#labels_dict={"COMM": "ls"}
#pancomm = panscript(labels_dict)
#pancomm.run()


class fmriprep_panscript(panscript):

    def __init__(self,labels_dict,name='fmriprep_panscript',params="",command="",execution={}):
        super().__init__(self,labels_dict,name=name,params=params,command=command)

        self.params = "--participant_label <PARTICIPANT_LABEL>" \
            " --output-spaces MNI152NLin6Asym:res-2 MNI152NLin2009cAsym:res-2 fsLR fsaverage anat func"\
            " --skip-bids-validation"\
            " --mem_mb <BIDSAPP_MEMORY>" \
            " --nthreads <BIDSAPP_THREADS>"\
            " --fs-license-file <FSLICENSE>"\
            " --omp-nthreads <BIDSAPP_THREADS>"\
            " -w <OUTPUT_DIR>/fmriwork"

        self.command = "singularity run --cleanenv --nv --no-home <FMRIPREP_CONTAINER>"\
                " <BIDS_DIR>"\
                " <OUTPUT_DIR>/fmrioutput"\
                " participant"

    def pre_run(self):
        print("pre run - setting template flow directory")
        TEMPLATEFLOW_HOME=getParams(self.labels_dict,"TEMPLATEFLOW_HOME")
        os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
        os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

        print("Creating output directory")
        output_dir = getParams(self.labels_dict,"OUTPUT_DIR")
        if os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def post_run(self):
        print("post run")

    def get_results(self):
        self.results = {}
        return self.results





