## HCP MMP1 Atlas in Freesurfer space

### Source
* 3498446.zip obtained from https://figshare.com/articles/dataset/HCP-MMP1_0_projected_on_fsaverage/3498446?file=5528837

* hcpmmp1_ordered.txt and hcpmmp1_original.txt obtained from mrtrix3.0.4 at /opt/mrtrix3/share/mrtrix3/labelconvert/


### Processing
unzip 3498446.zip to create:

* lh.HCP-MMP1.annot
* rh.HCP-MMP1.annot

this files are then used in function `create_3d_hcpmmp1_aseg` in `panprocessing.util_functions` to create a combined HCP MMP atlas and aseg atlas in subjects structural volumetric space. Freesurfer needs to have already run for this to work.


