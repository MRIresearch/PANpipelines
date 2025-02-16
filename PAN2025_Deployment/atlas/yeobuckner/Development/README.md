
Convert Yeo17, Yeo7,Buckner7 and Buckner 17 to FSL space
----------------------------------------------------

### Yeo Liberal Mask from https://surfer.nmr.mgh.harvard.edu/fswiki/CorticalParcellation_Yeo2011
### ftp://surfer.nmr.mgh.harvard.edu/pub/data/Yeo_JNeurophysiol11_MNI152.zip

panproc flirt -in $PWD/Yeo2011_7Networks_MNI152_FreeSurferConformed1mm_LiberalMask.nii.gz \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/yeo7_1mm.nii.gz \
      -applyxfm -usesqform -interp nearestneighbour 

panproc flirt -in $PWD/Yeo2011_17Networks_MNI152_FreeSurferConformed1mm_LiberalMask.nii.gz  \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/yeo17_1mm.nii.gz \
      -applyxfm -usesqform -interp nearestneighbour 

### Split label from https://github.com/ThomasYeoLab/CBIG/tree/master/stable_projects/brain_parcellation/Yeo2011_fcMRI_clustering/1000subjects_reference/Yeo_JNeurophysiol11_SplitLabels/MNI152

panproc flirt -in $PWD/Yeo2011_17Networks_N1000.split_components.FSL_MNI152_FreeSurferConformed_1mm.nii.gz \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/yeo17_splitlabel_1mm.nii.gz \
      -applyxfm -usesqform -interp nearestneighbour 

panproc flirt -in $PWD/Yeo2011_7Networks_N1000.split_components.FSL_MNI152_FreeSurferConformed_1mm.nii.gz \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/yeo7_splitlabel_1mm.nii.gz \
      -applyxfm -usesqform -interp nearestneighbour 

### Buckner Loose Mask from https://surfer.nmr.mgh.harvard.edu/fswiki/CerebellumParcellation_Buckner2011
### ftp://surfer.nmr.mgh.harvard.edu/pub/data/Buckner_JNeurophysiol11_MNI152.zip

panproc flirt -in $PWD/Buckner2011_17Networks_MNI152_FreeSurferConformed1mm_LooseMask.nii.gz \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/buck17_1mm.nii.gz \
      -applyxfm -usesqform -interp nearestneighbour 

panproc flirt -in $PWD/Buckner2011_7Networks_MNI152_FreeSurferConformed1mm_LooseMask.nii.gz \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/buck7_1mm.nii.gz \
      -applyxfm -usesqform -interp nearestneighbour 


### For comparison look at JHU atlas
#### Create 1mm version

panproc flirt -in $PWD/r_2mm_combined_corrected_atlas_1mm.nii \
      -ref /opt/fsl/data/standard/MNI152_T1_1mm.nii.gz \
      -out $PWD/r_1mm_combined_corrected_atlas_1mm.nii \
      -applyxfm -interp nearestneighbour -init $PWD/identity.mat




