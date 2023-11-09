echo "1 0 0 0" > eye.mat 
echo "0 1 0 0" >> eye.mat
echo "0 0 1 0" >> eye.mat
echo "0 0 0 1" >> eye.mat

REFERENCE=$PWD/tpl-MNI152NLin6Asym_res-01_T1w.nii.gz
INPUT=$PWD/AAL3v1_1mm.nii.gz
OUTPUT=$PWD/AAL3v1_1mm_MNI152NLin6Asym.nii.gz

neuroproc flirt -ref $REFERENCE -in $INPUT -applyxfm -init eye.mat -out $OUTPUT