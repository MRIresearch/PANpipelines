## AAL3 Atlas

### Source
AAL3v1 (https://www.oxcns.org/aal3.html) and files downloaded from https://www.oxcns.org/AAL3v1_for_SPM12.zip

### Notes
Please note that the original numbers in AAL2 for the anterior cingulate cortex (35, 36) and thalamus (81, 82) are left empty in AAL3,  as those voxels were substituted by the new subdivisions (Thalamic nuclei: 121-151; ACC: 151-156). Thus, the total number of parcellations in AAL3 is 166, with maximum label number 170. This ensures that most of the numbers used in AAL2 remain the same in AAL3, while AAL3 mainly adds new areas starting at number 121

This means in practice that when volume measures are obtained using this atlas the output CSV file will have 170 columns but values in columns 35,36,81 and 82 should be ignored. For multiple Comparison tests you will be performing 166 simulataneous tests rather than 170.


### Processing
Please see ./MNI152NLinAsym/Development/convert.sh for steps taken to create the atlas tpl-MNI152NLin6Asym_res-01_atlas-AAL3_dseg.nii.gz and tpl-MNI152NLin6Asym_res-02_atlas-AAL3_dseg.nii.gz. The original atlas at 1mm resolution was resliced to the same dimensions as the MNI152NLin6Asym atlas obtained from TemplateFlow. The original atlas at 2mm was just converted to RAS.

The file AAL3v1.nii.txt was edited to contain just the label names and renamed AAL3v1_1mm_index.txt for basic use in roi_mean_single.py

The file AAL3v1.nii.txt was edited to remove rois 35,36, 81 and 82 to create res-01_atlas-AAL3_dseg.tsv and res-02_atlas-AAL3_dseg.tsv with column names index and label for compatibility with other BIDS apps.