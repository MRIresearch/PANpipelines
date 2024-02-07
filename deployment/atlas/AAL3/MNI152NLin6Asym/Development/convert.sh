#!/bin/bash

# Download and unzip AAL3 Atlas
wget https://www.oxcns.org/AAL3v1_for_SPM12.zip
unzip AAL3v1_for_SPM12.zip


# Obtain MNI152NLin6Asym_ template
mkdir -p $PWD/TemplateFlow
python getTemplate $PWD/TemplateFlow --template_dict '{ "template": "MNI152NLin6Asym","suffix" : "T1w", "resolution" : 1, "extension" : [".nii.gz"]}'
REFERENCE=$PWD/tpl-MNI152NLin6Asym_res-01_T1w.nii.gz

echo "1 0 0 0" > eye.mat 
echo "0 1 0 0" >> eye.mat
echo "0 0 1 0" >> eye.mat
echo "0 0 0 1" >> eye.mat


INPUT=$PWD/AAL3/AAL3v1_1mm.nii.gz
OUTPUT=$PWD/tpl-MNI152NLin6Asym_res-01_atlas-AAL3_dseg.nii.gz

# reslice to same dimensions as template
neuroproc flirt -ref $REFERENCE -in $INPUT -applyxfm -init eye.mat -out $OUTPUT

# 2mm atlas - just convert to RAS
cp $PWD/AAL3/AAL3v1.nii.gz AAL3v1.nii.gz
neuroproc fslorient -swaporient $PWD/AAL3/AAL3v1.nii.gz
neuroproc fslswapdim $PWD/AAL3v1.nii.gz -x y z $PWD/AAL3v1_RAS.nii.gz 
mv $PWD/AAL3v1_RAS.nii.gz $PWD/tpl-MNI152NLin6Asym_res-02_atlas-AAL3_dseg.nii.gz

