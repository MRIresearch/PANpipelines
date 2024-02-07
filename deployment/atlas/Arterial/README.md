## Arterial Atlas
Liu et al 2023, Digital 3D Brain MRI Arterial Territories Atlas
https://www.nature.com/articles/s41597-022-01923-0

Data Downloaded from https://www.nitrc.org/frs/?group_id=1498
--------------------------------------------------------------
1. Release: ArterialAtlas_v2_MNI152, ReleaseDate: 2021-11-11 16:23, Filename: Atlas_MNI152.zip (9.35MB)
2. Release: VascularAtlasLabel_updated, ReleaseDate: 2022-05-26 04:20 Filename: ArterialAtlaslables.txt (3KB)

Processing Steps
----------------

1. Atlas_MNI152.zip extracted and ArterialAtlas.nii from folder ./Atlas_182_MNI located
2. ArterialAtlas.nii converted to int format and then to RAS

fslmaths $PWD/Atlas_182_MNI152/ArterialAtlas.nii $PWD/ArterialAtlas_int.nii.gz -odt int
cp $PWD/ArterialAtlas_int.nii.gz $PWD/ArterialAtlas_int_new.nii.gz
fslorient -swaporient $PWD/ArterialAtlas_int_new.nii.gz
fslswapdim $PWD/ArterialAtlas_int_new.nii.gz -x y z $PWD/tpl-MNI152NLin6Asym_res-01_atlas-Arterial_dseg.nii.gz

3. Resample to create 2mm version
ResampleImage 3 $PWD/tpl-MNI152NLin6Asym_res-01_atlas-arterial_dseg.nii.gz $PWD/tpl-MNI152NLin6Asym_res-02_atlas-Arterial_dseg.nii.gz 2x2x2 0 1 4

4. ArterialAtlasLables.txt renamed to ArterialAtlasLabels.txt and edited to retain just the ROI abbreviated labels in each row.

5. ArterialAtlasLables.txt renamed to res-01_atlas-Arterial_dseg.tsv and res-02_atlas-Arterial_dseg.tsv to create BIDS compliant labels

