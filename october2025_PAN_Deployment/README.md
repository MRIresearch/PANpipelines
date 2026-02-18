# Reproducing October 2025 MRI PAN Measures
The following [instructions](https://github.com/MRIresearch/PANpipelines/tree/main/october2025_PAN_Deployment) can be followed to replicate the results provided as part of the October 2025 data release on a slurm-based HPC environment. This release also made some amendments to the April 2025 release.

## Changes to April 2025 release
* New White Matter Hyperintensities (WMH) measures provided for April 2025 release.
* Subject HML0163 renamed to HML0162 for consistency with rest of Pan DB release.
* Subject HML0700 added to release.

## October 2025 release
* Updates provided for all previous tablles released in April 2025.
* New White Matter Hyperintensities (WMH) measures provided for October 2025 release.

## Tables released
* coree_chen_anat_measures.csv   (updated April 2025 release)
* coree_chen_anat_measures_20251001.csv (new October 2025 release)
* coree_chen_asl_measures.csv
* coree_chen_asl_measures_20251001.csv
* coree_chen_dwi_measures.csv
* coree_chen_dwi_measures_20251001.csv
* coree_chen_rsfmri_yeobuckner131_interconn_corticocereb.csv
* coree_chen_rsfmri_yeobuckner131_interconn_corticocereb_20251001.csv
* coree_chen_rsfmri_yeobuckner131_interconn_wholebrain.csv
* coree_chen_rsfmri_yeobuckner131_interconn_wholebrain_20251001.csv
* coree_chen_rsfmri_yeobuckner131_withinconn.csv
* coree_chen_rsfmri_yeobuckner131_withinconn_20251001.csv
* coree_chen_wmh_measures.csv
* coree_chen_wmh_measures_20251001.csv

## Create Root Directory
Create a root directory `ROOTDIR`from which you will reproduce the analysis. For this example we will create a directory in our Home directory.
```
ROOTDIR=$HOME/PanOctober
mkdir -p $ROOTDIR
```

## Create Python environment
Use a python virtual environment manager to create an environment for the panpipelines 1.1.6 release. Options include `virtualenv`, `conda`, `micromamba` etc. We will use `virtualenv` in this example.

### Install `virtualenv` and prepare virtual environment
Install `virtualenv` in python environment:
```
module load python/3.11/3.11.4
pip install --user virtualenv
```

Create a virtual environment (in our example we shall call it `pan_october2025_env`)  in a location defined by `ENVLOC`
```
ENVNAME=pan_october2025_env
ENVLOC=$ROOTDIR/venvs
mkdir -p $ENVLOC
module load python/3.11/3.11.4
virtualenv -p python3 $ENVLOC/$ENVNAME
```

Activate environment and Install version 1.1.6 of PAN pipelines using `pip`
```
module load python/3.11/3.11.4
source $ENVLOC/$ENVNAME/bin/activate
pip install panpipelines==1.1.6
```

## Deployment Folder Structure
For the October 2025 release we will be copying the data first from the `april2025_PAN_Deployment` folder and then appending additional files from `october2025_PAN_Deployment`

## Clone Panpipelines repository and copy folders
In a separate folder clone the Panpipelines repository and from the `april2025_PAN_Deployment` folder copy the folders   **atlas**, **batch_scripts** , **config**, **containers** and  **external_scripts** to your root directory.

Obtain the weights for the tractseg container by downloading  `tractseg_home.zip` from  the OSF PANpipeline repositiry at`https://osf.io/fpbkn/files/osfstorage` to the root directory and unzip it.

From `october2025_PAN_Deployment`, merge in the following **config**, **containers**, **external_scripts** and `runpan_october.sh` into your root directory. The files `external_scripts/amico/amico_noddi.py` and `containers/build_all.sh` will be overwritten.

## Prune unnecessary files
The following files should be removed as they are not necessary. If you decide to retain them then that is fine too as they will not be used. These files are as follows:

`runpan.sh` in the `ROOTDIR`.
`sessions.tsv` in `config` directory.
`pan.config.april2025` in `config` directory.


Your root directory should look like this now:

 <br/>
├── atlas<br/>
│   ├── Arterial <br/>
│   ├── freesurfer_atlas <br/>
│   ├── tractseg <br/>
│   └── xcpd_custom_atlases <br/>
├── batch_scripts <br/>
│   ├── group_template.pbs <br/>
│   ├── headers <br/>
│   └── participant_template.pbs <br/>
├── config <br/>
│   ├── PAN_dataset_description.json <br/>
│   ├── anatomical.py <br/>
│   ├── anatomical_interface.py <br/>
│   ├── april_october_combo.csv <br/>
│   ├── credentials
│   │   └── credentials.json
│   ├── freesurfer_outputs_april.csv <br/>
│   ├── gm_model.json <br/>
│   ├── hml_ids_list_241231.csv <br/>
│   ├── license.txt <br/>
│   ├── pan.config.oct2025 <br/>
│   ├── pan_eddyparams_cuda.json <br/>
│   └── style.css <br/>
├── containers <br/>
│   ├── build_all.sh<br/>
├── external_scripts <br/>
│   └── amico <br/>
│   └── wm_measures <br/>
├── runpan_october.sh <br/>
├── tractseg_home <br/>
├── venvs <br/>

## Create associated Apptainers
The PAN pipelines rely on a number of apptainer images which are required to successfully run the pipelines. These are available as docker images which can be converted to singularity images. Provided is an example for panprocminimal-v0.2.sif

```
export APPTAINER_CACHEDIR=$PWD/singularitycache 
SINGNAME=panprocminimal-v0.2.sif
DOCKERURI=docker://aacazxnat/panproc-minimal:0.2
singularity build $SINGNAME $DOCKERURI
```

The script `build_all.sh` in `containers` folder will enable you to build the containers. You will need a reasonable amount of memory to complete the build so obtain reasonable size of resources on the HPC before building.

The following singularity images should be generated and stored in an accessible location on your file system for example `/rootdir/containers`

`docker://aacazxnat/panproc-minimal:0.2` > `panprocminimal-v0.2.sif`

`docker://pennbbl/qsiprep:0.21.4` > `qsiprep-0.21.4.sif` 

`docker://nipreps/fmriprep:0.21.4` > `fmriprep-24.1.1.sif`

`docker://wasserth/tractseg_container:master` > `tractseg.sif` 

`docker://pennlinc/xcp_d:0.10.5` > `xcpd-0.10.5.sif`

`docker://aacazxnat/panproc-apps:0.1`   > `panapps.sif`

`docker://jqmcginnis/lst-ai:v1.2.0`   > `lstai.sif`


## Apptainer Provenance
Details of all the apptainers except 2 are provided in relevant references from the associated institutions. The other two apptainers  (`aacazxnat/panproc-minimal:0.2` and `aacazxnat/panproc-apps:0.1`) are custom made containers, the recipes for which are provided here https://github.com/MRIresearch/panproc-minimal (using v0.2 tag for this release) and https://github.com/MRIresearch/panproc-minimal/tree/main/panproc-apps respectively.

## Edit `pan.config.oct2025`
If the above folder configuration is used then there should be minimal changes in the the config file.  Please update the `CONTAINER_DIR` reference for example if you have built the containers in another location other than `<rootdir>/containers`

## Edit `credentials.json` in `credentials` directory
Change `USERNAME` and `PASSWORD` to your XNAT access credentials. You may also want to change the access permissions of the `credentials` folder to `500` and the `credentials.json` file to `400` if you are on a shared system.

## Freesurfer license
Update the provided freesurfer license in `<rootdir>/config/license.txt` with your personal license if you have one. The pipeline will run with the existing license but it is good practice to use your own license. You can get a license from the Freesurfer main website.

## Edit runpan_october.sh
Add/amend commands required to instantiate your python environment e.g. module load env, conda activate env, source env etc. In the provided example `source /xdisk/trouard/chidiugonna/PAN/oct2025_repro/venvs/pan_oct2025_env/bin/activate` is defined and this will need to be changed to match your own environment.

Change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`

Change `PKG_DIR` to point to the directory that contains the pipelines package:
`PKG_DIR=[Path to]/PANpipelines/src`. This will be in your conda or python or virtual env environment if you installed PANpipelines using `pip`. If you are using the code directly from the repository then this will be the path to the cloned repository.

If you have decided not to install the PANpipelines package but have downloaded the repository then add the path to the `src` folder in the `PYTHONPATH` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

## Edit  slurm templates in ./batch_script
Edit `group_template.pbs` and `participant_template.pbs` and add commands required to instantiate your python environment e.g. module load env, conda activate env, source env  etc. In the provided examples `source /xdisk/trouard/chidiugonna/PAN/oct2025_repro/venvs/pan_oct2025_env/bin/activate` is defined and this will need to be changed to match your own environment.

Also change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`

If you have decided not to install the PANpipelines package but have downloaded the repository then you may need to add the path to the `src` folder in the `PYTHONPATH` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

## Edit  batch_scripts/headers
Go through each of the different slurm headers to adjust times and credentials as necessary. These are referenced in the config entries as `SLURM_CPU_HEADER` and `SLURM_GPU_HEADER` as required.

##  Deploy
run as `./runpan_october.sh`. The script is currently set to run a selection of 10 subjects. To run all subjects then use "ALL_SUBJECTS" in the participant variable. Please note that some SLURM configurations place limits on the numbers of jobs that can be run. Each subject will require about 40 jobs for the single subject pipeline. And there are 11 group jobs. So for N subjects a total of `40*N + 11` Jobs will be required. To run all the subjects you may need to run them in batches of Nmax depending on your SLURM constraints and pass different participants to run using the setting `SESSIONSFILE="--sessions_file $CURRDIR/config/sessions.tsv"` with a different `sessions.tsv` file for each batch.

Another approach is to use the `--participant_query` parameter. For example this parameter `-participant_query (df.hml_id.isin([<PARTICIPANTS>])) & (df.index > 0) & (df.index < 41)` will select all patients specified in the `--participants_label` parameter and that have index between `1` and `40`.


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.

if you see this error `ImportError: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips  26 Jan 2017'. See: https://github.com/urllib3/urllib3/issues/2168` and you are using `Python 3.7 - 3.9` on the HPC then downgrade `urllib3` as follows `pip install urllib==1.25.9` 

# General HPC Deployment
As described in the main README, one of the current limitations of the pipeline is the fact that it has been tested on **SLURM** environments in which singularity containers are automatically bound by the system administrator to disk locations on which users manage their data. There is however support for the use of the `-B` parameter  to map output locations to their respective locations within the singularity image. This functionality will attempt to automatically translate all host location parameters in a command call to their container locations. This has not been extensively tested and so should be used with caution.
