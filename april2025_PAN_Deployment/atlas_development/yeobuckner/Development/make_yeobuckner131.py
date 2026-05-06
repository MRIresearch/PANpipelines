#Create yeobuckner131

#Atlas combines 114-network Yeo Cerebral atlas with the 17-network Buckner Cerebellar atlas. Areas of overlap between cerebellum and cerebrum are resolved by assigning cerebellar values to the overlapping voxels.

import nibabel as nib
import numpy as np
import pandas as pd

def reorient(input_file, ori, out_file=None):
    from nipype.interfaces.image import Reorient
    from nipype import Node
    import os

    reorient_node = Node(Reorient(),name="reorient_to_{}".format(ori))
    reorient_node.inputs.in_file =  os.path.abspath(input_file)
    reorient_node.inputs.orientation=ori
    reorient_results = reorient_node.run()
    results_file = os.path.abspath(reorient_results.outputs.out_file)
    if out_file:
        out_file = os.path.abspath(out_file)
        os.system(f"mv {results_file} {out_file}")
    else:
        out_file = results_file
    
    return out_file


# Get the label file from -> https://github.com/ThomasYeoLab/CBIG/blob/master/stable_projects/brain_parcellation/Yeo2011_fcMRI_clustering/1000subjects_reference/Yeo_JNeurophysiol11_SplitLabels/Yeo2011_17networks_N1000.split_components.glossary.csv
label_file = "./sources/Originals/Yeo2011_17networks_N1000.split_components.glossary.csv"
yeo_df = pd.read_table(label_file,sep=",")

# Get the atls file from -> https://github.com/ThomasYeoLab/CBIG/tree/master/stable_projects/brain_parcellation/Yeo2011_fcMRI_clustering/1000subjects_reference/Yeo_JNeurophysiol11_SplitLabels/MNI152/Yeo2011_17Networks_N1000.split_components.FSL_MNI152_1mm.nii.gz
atlas_file = "./sources/Yeo2011_17Networks_N1000.split_components.FSL_MNI152_1mm.nii.gz"
atlas_img = nib.load(atlas_file)
atlas_data = atlas_img.get_fdata()

label_dict = {"VisCent": 1,
            "VisPeri":2,
            "SomMotA":3,           
            "SomMotB":4,     
            "DorsAttnA":5,     
            "DorsAttnB":6,    
            "SalVentAttnA":7,     
            "SalVentAttnB":8,
            "LimbicA":9,     
            "LimbicB":10,  
            "ContC":11,    
            "ContA":12,     
            "ContB":13,  
            "DefaultD":14,  
            "DefaultC":15,  
            "DefaultA":16,  
            "DefaultB":17  
}

yeo131_df=yeo_df.copy()
yeo131_df["17Networks Number"]=0
yeo131_df["17Networks Name"]=yeo131_df["Network Name"]

replacement_dict = {"central": "VisCent",
            "peripheral": "VisPeri",
            "somatomotor A": "SomMotA",           
            "somatomotor B": "SomMotB",     
            "dorsal attention A": "DorsAttnA",     
            "dorsal attention B": "DorsAttnB",    
            "ventral attention A": "SalVentAttnA",     
            "ventral attention B": "SalVentAttnB",
            "limbic A": "LimbicA",     
            "limbic B": "LimbicB",  
            "control A": "ContA",     
            "control B": "ContB",  
            "control C": "ContC",     
            "default A": "DefaultA",  
            "default B": "DefaultB",  
            "default C": "DefaultC",  
            "temporal parietal": "DefaultD"  
}


import re
def replace_location(value):
    if not pd.isna(value):
        value = re.sub(r'\s+', ' ', value).strip()
        for key, replacement in replacement_dict.items():
            if key.lower() in value.lower():
                return replacement
    return value


yeo131_df["17Networks Name"] = yeo131_df["17Networks Name"].apply(replace_location)
yeo131_df["17Networks Number"] = yeo131_df["17Networks Name"].map(label_dict)

# Special Case to handle
yeo131_df.iloc[114,yeo131_df.columns.get_loc("Label Name")] = "17Networks_RH_DefaultD_TempPar"
yeo131_df.iloc[57,yeo131_df.columns.get_loc("Label Name")] = "17Networks_LH_DefaultD_TempPar"

startroi=115
netlen=17
rows=[]
for cereb in range(startroi,startroi+netlen):
    netnum = cereb - 114
    netname = [x for x in label_dict.keys() if label_dict[x]==netnum][0]
    rows.append({"Label Name" : f"17Networks_{netname}_Cerebellum_{netnum}", 
                 "Network Name": f"{netname}",
                 "Full Component Name" : f"Cerebellum_{netnum}",
                 "17Networks Number" : 	netnum,
                 "17Networks Name": netname}
               )


yeo131_df = pd.concat([yeo131_df, pd.DataFrame(rows)], ignore_index=True)


# Create new glossary file for the atlas
yeo131_df.to_csv("./outputs/17networks_yeobuckner131_glossary.csv",sep=",",header=True, index=False)

# Add Cerebellar Atlas

# get buckner atlas from -> ftp://surfer.nmr.mgh.harvard.edu/pub/data/Buckner_JNeurophysiol11_MNI152.zip
# Buckner2011_17Networks_MNI152_FreeSurferConformed1mm_LooseMask.nii.gz transformed and then transform to  FSL LAS Space as follows

#  flirt -in Buckner2011_17Networks_MNI152_FreeSurferConformed1mm_LooseMask.nii.gz \
#      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
#      -out Buckner2011_17Networks_FSL_MNI152_1mm.nii.gz \
#      -applyxfm -usesqform -interp nearestneighbour


buck_file = "./sources/Buckner2011_17Networks_FSL_MNI152_1mm.nii.gz "
buck_img = nib.load(buck_file)
buck_data = buck_img.get_fdata()

for roinum in range(1,1+netlen):
    buck_data[buck_data == roinum]=roinum+114

# Merge atlases
yeo_data = atlas_data + buck_data

# handle overlap between both atlases
mask1=atlas_data > 0
mask2=buck_data > 0
combined_mask = np.logical_and(mask1,mask2)

# Where atlases overlap, keep buckner atlas priority
yeo_data[combined_mask]=buck_data[combined_mask]

# atlas in LAS format
final_img = nib.Nifti1Image(yeo_data, atlas_img.affine, atlas_img.header)
nib.save(final_img, "./outputs/atlas-yeobuckner131_space-MNI152NLin6Asym_res-01_ori-LAS_dseg.nii.gz")

# create label file for new combined atlas
yeo131_labeldf = pd.DataFrame(range(1,132),columns=["index"])
yeo131_labeldf["label"] = [x for x in yeo131_df["Label Name"] if x.startswith('17Networks')]
yeo131_labeldf.to_csv("./outputs/atlas-yeobuckner131_dseg.tsv",sep="\t",header=True, index=False)

# atlas in RAS format which is compatible with most software
input_file = "./outputs/atlas-yeobuckner131_space-MNI152NLin6Asym_res-01_ori-LAS_dseg.nii.gz"
out_file="./outputs/atlas-yeobuckner131_space-MNI152NLin6Asym_res-01_dseg.nii.gz"
final = reorient(input_file, "RAS", out_file)





