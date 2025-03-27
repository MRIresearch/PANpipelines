from nipype.interfaces.base import BaseInterfaceInputSpec, BaseInterface, File, TraitedSpec, traits
from nipype import Node
from panpipelines.utils.util_functions import *
import os
import glob
import numpy as np 
import nibabel as nib
import pandas as pd
import json
import datetime
from pathlib import Path
from nipype import logging as nlogging

IFLOGGER=nlogging.getLogger('nipype.interface')

newnet7 = {
    "1" : {
        "netname": ["Vis"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.Vis"
    },
    "2" : {
        "netname": ["Def"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.Def"
    },
    "3" : {
        "netname": ["SomMot"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.SomMot"
    },
    "4" : {
        "netname": ["Cont"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.Cont"
    },
    "5" : {
        "netname": ["DorsAttn"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.DorsAttn"
    },
    "6" : {
        "netname": ["Limbic"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.Limbic"
    },
    "7" : {
        "netname": ["SalVentAttn"],
        "exclusions" : ["Cerebellum"],
        "newname" : "Cortical.SalVentAttn"
    },
    "8" : {
        "netname": ["Vis","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.Vis"
    },
    "9" : {
        "netname": ["Def","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.Def"
    },
    "10" : {
        "netname": ["SomMot","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.SomMot"
    },
    "11" : {
        "netname": ["Cont","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.Cont"
    },
    "12" : {
        "netname": ["DorsAttn","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.DorsAttn"
    },
    "13" : {
        "netname": ["Limbic","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.Limbic"
    },
    "14" : {
        "netname": ["SalVentAttn","Cerebellum"],
        "exclusions" : [],
        "newname" : "Cereb.SalVentAttn"
    }
}
net17= ["VisPeri","VisCent","DefaultA","DefaultB","DefaultC","TempPar","SomMotA","SomMotB","ContA","ContB","ContC","DorsAttnA","DorsAttnB","LimbicA","LimbicB","SalVentAttnA","SalVentAttnB"]
net7 = ["Vis","Def","SomMot","Cont","DorsAttn","Limbic","SalVentAttn"]

def addExtraCols(df,labels_dict,subject,session):
    df = processExtraColumns(df, labels_dict)
    if session: 
        df.insert(0,"session_id",[session for x in range(len(df))])
    if subject:
        df.insert(0,"subject_id",[subject for x in range(len(df))])
    return df

def calculate_custom_interconnectivity(corrdf,net=newnet7,nodecol="Node"):
    inter_df=pd.DataFrame()
    table_vals=[]
    table_cols=[]

    nodeidxs = net.keys()
    nodepairs = intranode_pairings(nodeidxs)
   
    for pair in nodepairs:
        idx1=pair[0]
        idx2=pair[1]
        netname1 = net[idx1]["netname"]
        netname2 = net[idx2]["netname"]
        new_netname1 = net[idx1]["newname"]
        new_netname2 = net[idx2]["newname"]
        exclusions1 = net[idx1]["exclusions"]
        exclusions2 = net[idx2]["exclusions"]

        netnodes1 = [x for x in corrdf.columns if all(y.lower() in x.lower() for y in netname1) and not any(y.lower() in x.lower() for y in exclusions1) ]
        netnodes2 = [x for x in corrdf.columns if all(y.lower() in x.lower() for y in netname2) and not any(y.lower() in x.lower() for y in exclusions2) ]
        
        if len(netnodes1) > 0 and len(netnodes2) > 0:
            intercorr = calc_inter(corrdf,netnodes1,netnodes2)
            table_cols.append(f"{new_netname1}_{new_netname2}")
            table_vals.append(intercorr)
        else:
            IFLOGGER.warn(f"Cannot calculate inter-regional connectivity with missing nodes - netnode1:{netnodes1} netnode2:{netnodes2}")
            table_cols.append(f"{new_netname1}_{new_netname2}")
            table_vals.append(np.nan)
    if table_cols and table_vals:
        inter_df = pd.DataFrame([table_vals])
        inter_df.columns = table_cols
    return inter_df

def calculate_yeobuckner_interconnectivity(corrdf,net=net7,nodecol="Node",prefix="intra",exception=None,addition=None):
    inter_df=pd.DataFrame()
    table_vals=[]
    table_cols=[]

    nodepairs = intranode_pairings(net7)
   
    for pair in nodepairs:
        netname1=pair[0]
        netname2=pair[1]
        if exception:
            netnodes1 = [ x for x in corrdf.columns if netname1.lower() in x.lower() and exception.lower() not in x.lower()]
            netnodes2 = [ x for x in corrdf.columns if netname2.lower() in x.lower() and exception.lower() not in x.lower()]

        elif addition:
            netnodes1 = [ x for x in corrdf.columns if netname1.lower() in x.lower() and addition.lower() in x.lower()]
            netnodes2 = [ x for x in corrdf.columns if netname2.lower() in x.lower() and addition.lower() in x.lower()]
        else:
            netnodes1 = [ x for x in corrdf.columns if netname1.lower() in x.lower()]
            netnodes2 = [ x for x in corrdf.columns if netname2.lower() in x.lower()]
        if len(netnodes1) > 0 and len(netnodes2) > 0:
            intercorr = calc_inter(corrdf,netnodes1,netnodes2)
            table_cols.append(f"{prefix}.{netname1}_{netname2}")
            table_vals.append(intercorr)
        else:
            IFLOGGER.warn(f"Cannot calculate inter-regional connectivity with missing nodes - netnode1:{netnodes1} netnode2:{netnodes2}")
            table_cols.append(f"{prefix}.{netname1}_{netname2}")
            table_vals.append(np.nan)
    if table_cols and table_vals:
        inter_df = pd.DataFrame([table_vals])
        inter_df.columns = table_cols
    return inter_df

def calculate_yeobuckner_intraconnectivity(corrdf,net=net7,nodecol="Node",prefix="intra",exception=None,addition=None):
    intra_df=pd.DataFrame()
    table_vals=[]
    table_cols=[]
    for netname in net:
        if exception:
            netnodes = [ x for x in corrdf.columns if netname.lower() in x.lower() and exception.lower() not in x.lower()]
        elif addition:
            netnodes = [ x for x in corrdf.columns if netname.lower() in x.lower() and addition.lower() in x.lower()]
        else:
            netnodes = [ x for x in corrdf.columns if netname.lower() in x.lower()]
        if len(netnodes) > 1:
            intracorr = calc_intra(corrdf,netnodes)
            table_cols.append(f"{prefix}_{netname}")
            table_vals.append(intracorr)
        else:
            IFLOGGER.warn(f"Cannot calculate intra-regional connectivity with 1 node - {netnodes}")
            table_cols.append(f"{prefix}_{netname}")
            table_vals.append(np.nan)
    if table_cols and table_vals:
        intra_df = pd.DataFrame([table_vals])
        intra_df.columns = table_cols
    return intra_df

def postxcpd_proc(labels_dict,input_dir):

    cwd=os.getcwd()
    labels_dict = updateParams(labels_dict,"CWD",cwd)
    output_dir=cwd
    participant_label = getParams(labels_dict,'PARTICIPANT_LABEL')
    subject = f"sub-{participant_label}"
    session_label = getParams(labels_dict,'PARTICIPANT_SESSION')
    input_dir=substitute_labels(input_dir,labels_dict)

    if not session_label:
        session=None
        postxcpd_outputdir = os.path.join(cwd,f"{subject}_postxcpd_outdir")
    else:
        session = f"ses-{session_label}"
        postxcpd_outputdir = os.path.join(cwd,f"{subject}_{session}_postxcpd_outdir")

    if not os.path.isdir(postxcpd_outputdir):
        os.makedirs(postxcpd_outputdir,exist_ok=True)

    try:
        atlases=[x for x in os.listdir(os.path.join(input_dir,"atlases")) if x.startswith("atlas-" )]
    except Exception as exc:
        atlases=[]

    for atlas in atlases:
        atlasstub = atlas.split("-")[1]

        replacecol={}
        atlas_config=getParams(labels_dict,atlasstub)
        if atlas_config:
            if "replacecol" in atlas_config.keys():
                replacecol = atlas_config["replacecol"]
        else:
            continue

        rehopath = os.path.join(input_dir,subject,session,"func",f"{subject}_{session}_*{atlasstub}*reho_bold.tsv")
        rehofile=glob.glob(rehopath)
        if rehofile:
            rehofile = rehofile[0]
            rehodf=pd.read_table(rehofile,sep="\t")
            rehodf = addExtraCols(rehodf,labels_dict,subject,session)
            reho_out = newfile(outputdir=postxcpd_outputdir,assocfile=rehofile,extension="csv")
            rehodf.to_csv(reho_out ,sep=",",header=True, index=False)

        alffpath = os.path.join(input_dir,subject,session,"func",f"{subject}_{session}_*{atlasstub}*alff_bold.tsv")
        alfffile=glob.glob(alffpath)
        if alfffile:
            alfffile = alfffile[0]
            alffdf=pd.read_table(alfffile,sep="\t")
            alffdf = addExtraCols(alffdf,labels_dict,subject,session)
            alff_out = newfile(outputdir=postxcpd_outputdir,assocfile=alfffile,extension="csv")
            alffdf.to_csv(alff_out ,sep=",",header=True, index=False)

        coverpath = os.path.join(input_dir,subject,session,"func",f"{subject}_{session}_*{atlasstub}*coverage_bold.tsv")
        coverfile=glob.glob(coverpath)
        if coverfile:
            coverfile = coverfile[0]
            coverdf=pd.read_table(coverfile,sep="\t")
            coverflatdf=transpose(coverdf)
            coverflatdf = addExtraCols(coverflatdf,labels_dict,subject,session)
            flatcover = newfile(outputdir=postxcpd_outputdir,assocfile=coverfile,extension="csv")
            coverflatdf.to_csv(flatcover,sep=",",header=True, index=False)

        corrpath = os.path.join(input_dir,subject,session,"func",f"{subject}_{session}_*{atlasstub}*relmat.tsv")
        corrfile=glob.glob(corrpath)
        if corrfile:
            corrfile = corrfile[0]
            corrdf=pd.read_table(corrfile,sep="\t")
            flatdf=flatten(corrdf,replace=replacecol)
            flatdf = addExtraCols(flatdf,labels_dict,subject,session)
            flatcorr = newfile(outputdir=postxcpd_outputdir,assocfile=corrfile,suffix="desc-flat",extension="csv")
            flatdf.to_csv(flatcorr,sep=",",header=True, index=False)
        
        # if this is a yeobuckner 131 atlas - we will calculate the intra-regional connectivity based on net7 and net17
        if "yeobuckner131" in atlasstub:
            intra_wholebrain_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net7,nodecol="Node",prefix="wholeintra")
            intra_wholebrain_df = addExtraCols(intra_wholebrain_df,labels_dict,subject,session)

            intra_cortical_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net7,nodecol="Node",prefix="corticalintra",exception="Cerebellum")
            yeo131_net7_intradf = pd.concat([intra_wholebrain_df,intra_cortical_df],axis=1)

            intra_cerebellum_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net7,nodecol="Node",prefix="cerebintra",addition="Cerebellum")
            yeo131_net7_intradf = pd.concat([yeo131_net7_intradf,intra_cerebellum_df],axis=1)

            yeo131_net7= os.path.join(postxcpd_outputdir,f"{subject}_{session}_{atlasstub}_Networks7_intraconnectivity.csv")
            yeo131_net7_intradf.to_csv(yeo131_net7,sep=",",header=True, index=False)

            intra_wholebrain_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net17,nodecol="Node",prefix="wholeintra")
            intra_wholebrain_df = addExtraCols(intra_wholebrain_df,labels_dict,subject,session)

            intra_cortical_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net17,nodecol="Node",prefix="corticalintra",exception="Cerebellum")
            yeo131_net17_intradf = pd.concat([intra_wholebrain_df,intra_cortical_df],axis=1)

            yeo131_net17= os.path.join(postxcpd_outputdir,f"{subject}_{session}_{atlasstub}_Networks17_intraconnectivity.csv")
            yeo131_net17_intradf.to_csv(yeo131_net17,sep=",",header=True, index=False)

            # we also calculate the inter-regional connectivity
            inter_wholebrain_df = calculate_yeobuckner_interconnectivity(corrdf,net=net7,nodecol="Node",prefix="wholeinter")
            inter_wholebrain_df = addExtraCols(inter_wholebrain_df,labels_dict,subject,session)

            #inter_cortical_df = calculate_yeobuckner_interconnectivity(corrdf,net=net7,nodecol="Node",prefix="corticalinter",exception="Cerebellum")
            #yeo131_net7_interdf = pd.concat([inter_wholebrain_df,inter_cortical_df],axis=1)

            #inter_cerebellum_df = calculate_yeobuckner_interconnectivity(corrdf,net=net7,nodecol="Node",prefix="cerebinter",addition="Cerebellum")
            #yeo131_net7_interdf = pd.concat([yeo131_net7_interdf,inter_cerebellum_df],axis=1)

            yeo131_net7_inter= os.path.join(postxcpd_outputdir,f"{subject}_{session}_{atlasstub}_Networks7_wholebrain_interconnectivity.csv")
            inter_wholebrain_df.to_csv(yeo131_net7_inter,sep=",",header=True, index=False)

            inter_newwholebrain_df = calculate_custom_interconnectivity(corrdf,net=newnet7,nodecol="Node")
            inter_newwholebrain_df  = addExtraCols(inter_newwholebrain_df ,labels_dict,subject,session)
            inter_newwholebrain= os.path.join(postxcpd_outputdir,f"{subject}_{session}_{atlasstub}_Networks7_corticocerebellar_interconnectivity.csv")
            inter_newwholebrain_df.to_csv(inter_newwholebrain,sep=",",header=True, index=False)


        # if this is a yeobuckner 131 atlas - we will calculate the intra-regional connectivity based on net7 and net17
        if "yeobuckner58" in atlasstub:
            intra_wholebrain_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net7,nodecol="Node",prefix="wholeintra")
            intra_wholebrain_df = addExtraCols(intra_wholebrain_df,labels_dict,subject,session)

            intra_cortical_df = calculate_yeobuckner_intraconnectivity(corrdf,net=net7,nodecol="Node",prefix="corticalintra",exception="Cerebellum")
            yeo58_net7_intradf = pd.concat([intra_wholebrain_df,intra_cortical_df],axis=1)

            yeo58_net7= os.path.join(postxcpd_outputdir,f"{subject}_{session}_{atlasstub}_Networks7_intraconnectivity.csv")
            yeo58_net7_intradf.to_csv(yeo58_net7,sep=",",header=True, index=False)

        atlaspath = os.path.join(input_dir,"atlases",f"{atlas}",f"{atlas}*.nii.gz")
        atlasfile=glob.glob(atlaspath)
        labelpath = os.path.join(input_dir,"atlases",f"{atlas}",f"{atlas}*.tsv")
        labelfile=glob.glob(labelpath)
        if atlasfile and labelfile:
            atlasfile=atlasfile[0]
            labelfile=labelfile[0]
            roisizes_df = roisizes(atlasfile,labelfile)
            roisizes_file = os.path.join(postxcpd_outputdir,f"{subject}_{session}_{atlasstub}_roisizes.csv")
            roisizes_df.to_csv(roisizes_file,sep=",",header=True, index=False)
        
    out_files=[]

    return {
        "output_dir":output_dir,
        "out_files":out_files
    }


class postxcpdInputSpec(BaseInterfaceInputSpec):
    labels_dict = traits.Dict({},mandatory=False,desc='labels', usedefault=True)
    input_dir = traits.String("",desc="XCPD Output Directory", usedefault=True)


class postxcpdOutputSpec(TraitedSpec):
    output_dir = traits.String(desc='output dir')
    out_files = traits.List(desc='list of files')
    
class postxcpd_pan(BaseInterface):
    input_spec = postxcpdInputSpec
    output_spec = postxcpdOutputSpec

    def _run_interface(self, runtime):

        # Call our python code here:
        outputs = postxcpd_proc(
            self.inputs.labels_dict,
            self.inputs.input_dir
        )

        setattr(self, "_results", outputs)
        # And we are done
        return runtime

    def _list_outputs(self):
        return self._results


def create(labels_dict,name="postxcpd_node",input_dir=""):
    # Create Node
    pan_node = Node(postxcpd_pan(), name=name)

    if LOGGER:
        LOGGER.info(f"Created Node {pan_node!r}")
        
    # Specify node inputs
    pan_node.inputs.labels_dict = labels_dict
    if input_dir is None:
        input_dir = ""       
    pan_node.inputs.input_dir =  input_dir

    return pan_node


