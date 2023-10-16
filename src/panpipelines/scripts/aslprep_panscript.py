from panpipelines.utils.util_functions import *
from panpipelines.scripts.panscript import *
import os
import glob
from bids import BIDSLayout
import json
import nibabel
import pandas as pd
# TEST
#from panpipelines.scripts import *
#SCRIPT="fmriprep_panscript"
#panscript=eval("{}.{}".format(SCRIPT,SCRIPT))
#labels_dict={"COMM": "ls"}
#pancomm = panscript(labels_dict)
#pancomm.run()

class aslprep_panscript(panscript):

    def __init__(self,labels_dict,name='fmriprep_panscript',params="",command="",execution={}):
        super().__init__(self,labels_dict,name=name,params=params,command=command)

        self.params = "--participant_label <PARTICIPANT_LABEL>" \
            " --low-mem"\
            " --skip-bids-validation"\
            " --stop-on-first-crash" \
            " --use-syn-sdc"\
            " --fs-license-file <FSLICENSE>"\
            " --ignore fieldmaps"\
            " -w <OUTPUT_DIR>/aslprep_work"

        self.command = "singularity run --cleanenv --nv --no-home <ASLPREP_CONTAINER>"\
                " <BIDS_DIR>"\
                " <OUTPUT_DIR>/aslprep_output"\
                " participant"

        self.asl_bids_changes = {
            "acq-prod" : {
                "BolusCutOffDelayTechnique": "QUIPSSII",
                "BolusCutOffTechnique": "QUIPSSII",
                "M0Type" : "Separate",
                "RepetitionTimePreparation": { 
                    "choices" : [["field","RepetitionTimeExcitation"],["field","RepetitionTime"],["float",4]]
                }
            },
            "acq-pcasl" : {
                "M0Type" : "Separate",
                "RepetitionTimePreparation": {
                    "choices" : [["field","RepetitionTimeExcitation"],["field","RepetitionTime"],["float",4.2]]
                }
            },
        }

        self.m0_bids_changes = {
            "acq-prod" : {
                "RepetitionTimePreparation": { 
                    "choices" : [["field","RepetitionTimeExcitation"],["field","RepetitionTime"],["float",4]]
                }
            },
            "acq-pcasl" : {
                "RepetitionTimePreparation": {
                    "choices" : [["field","RepetitionTimeExcitation"],["field","RepetitionTime"],["float",10]]
                }
            },
        }

        self.aslcontext_dict = {
            "acq-prod" : "control:label",
            "acq-pcasl" : "label:control"
        }

    def pre_run(self):
        print("pre run - setting template flow directory")
        TEMPLATEFLOW_HOME=getParams(self.labels_dict,"TEMPLATEFLOW_HOME")
        os.environ["TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME
        os.environ["SINGULARITYENV_TEMPLATEFLOW_HOME"]=TEMPLATEFLOW_HOME

        # change fsl out type - important as some aslprep nodes are expecting .nii.gz explictly
        os.environ["FSLOUTPUTTYPE"]="NIFTI_GZ"
        os.environ["SINGULARITYENV_FSLOUTPUTTYPE"]="NIFTI_GZ"
        #Environment variable SINGULARITYENV_FSLOUTPUTTYPE= is set, but APPTAINERENV_FSLOUTPUTTYPE= is preferred

        print("Creating output directory")
        output_dir = getParams(self.labels_dict,"OUTPUT_DIR")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        bids_dir = getParams(self.labels_dict,"BIDS_DIR")
        participant_label = getParams(self.labels_dict,"PARTICIPANT_LABEL")

        layout = BIDSLayout(bids_dir)
        asl=layout.get(subject=participant_label,suffix='asl', extension='nii.gz')

        if len(asl) > 0:
            asl_entities = asl[0].get_entities()
            if "acquisition" in asl_entities.keys():
                asl_acq = "acq-" + asl_entities["acquisition"]
            else:
                asl_acq = get_bidstag("acq",asl[0].filename)

            # Edit metadata 
            asl_assocs = asl[0].get_associations()
            asl_json_choice = [x.path for x in asl[0].get_associations() if x.entities['extension']==".json"]
            if not asl_json_choice  is None and len(asl_json_choice ) > 0:
                asl_json_file=asl_json_choice[0]
            else:
                asl_entities['extension']=".json"
                asl_json_choice  = layout.get(return_type='file', invalid_filters='allow', **asl_entities)
                if not asl_json_choice  is None and len(asl_json_choice ) > 0:
                    asl_json_file=asl_json_choice[0]

            if not asl_json_file is None and len(asl_json_file) > 0:
                with open(asl_json_file, 'r') as infile:
                    asl_json = json.load(infile) 

                asl_bids_amendments = self.asl_bids_changes[asl_acq]
                for itemkey, itemvalue in asl_bids_amendments.items():
                    if isinstance(itemvalue,dict):
                        if "choices" in itemvalue.keys():
                            choice_list = itemvalue["choices"]
                            for choice in choice_list:
                                field_type=choice[0]
                                field_name=choice[1]
                                if field_type == "field":
                                    if field_name in asl_json.keys():
                                        asl_json[itemkey]=asl_json[field_name]
                                        break
                                else:
                                    varvalue = get_value_bytype(field_type,field_name)
                                    if varvalue is not None:
                                        asl_json[itemkey]=varvalue

                        else:
                            asl_json[itemkey] = itemvalue
                    else:
                        asl_json[itemkey] = itemvalue


                with open(asl_json_file, 'w') as outfile:
                    json.dump(asl_json, outfile ,indent=2)

            else:
                print("No asl json file found.")

            # create aslcontext file
            asl_entities['extension']=".tsv"
            asl_entities['suffix']="aslcontext"
            aslcontext_filepath = layout.build_path(asl_entities)

            asl_img = nibabel.load(asl[0])
            asl_volumes = asl_img.shape[3]
            aslcontext_order = self.aslcontext_dict[asl_acq]
            aslcontext_header = ["volume_type"]
            aslcontext_values = []
            if aslcontext_order == "control:label":
                for count in range(asl_volumes):
                    if count%2 == 0:
                        aslcontext_values.append("control")
                    else:
                        aslcontext_values.append("label")
            elif aslcontext_order == "label:control":
                for count in range(asl_volumes):
                    if count%2 == 0:
                        aslcontext_values.append("label")
                    else:
                        aslcontext_values.append("control")

            aslcontext_df = pd.DataFrame(aslcontext_values,columns = aslcontext_header)
            aslcontext_df.to_csv(aslcontext_filepath,sep="\t",header=True, index=False)

            #m0_choice = [x.path for x in asl[0].get_associations() if x.entities['suffix']=="m0scan"]

        else:
            print("No asl file found.")




    
    def post_run(self):
        print("post run")

    def get_results(self):
        self.results = {}
        return self.results





