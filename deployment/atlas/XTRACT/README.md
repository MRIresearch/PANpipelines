## XTRACT

### Source
xtract-tract-atlases-maxprob5-1mm.nii.gz from $FSLDIR/data/atlases/XTRACT
The file XTRACT.xml from $FSLDIR/data/atlases/XTRACT edited to create XTRACT_index.txt with just the roi labels

### Processing
cp $PWD/xtract-tract-atlases-maxprob5-1mm.nii.gz $PWD/xtract-tract-atlases-maxprob5-1mm_new.nii.gz
fslorient -swaporient $PWD/xtract-tract-atlases-maxprob5-1mm_new.nii.gz
fslswapdim $PWD/xtract-tract-atlases-maxprob5-1mm_new.nii.gz -x y z $PWD/tpl-MNI152NLin6Asym_res-01_atlas-XTRACT_dseg.nii.gz

3. Resample to create 2mm version
ResampleImage 3 $PWD/tpl-MNI152NLin6Asym_res-01_atlas-XTRACT_dseg.nii.gz $PWD/tpl-MNI152NLin6Asym_res-02_atlas-XTRACT_dseg.nii.gz 2x2x2 0 1 4


