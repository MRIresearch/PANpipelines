# Reproducing April 2025 MRI PAN Measures
The following [instructions](https://github.com/MRIresearch/PANpipelines/tree/main/april2025_PAN_Deployment) can be followed to replicate the results provided as part of the April 2025 data release on a slurm-based HPC environment.

## Tables released

* coree_chen_anat_measures.csv
* coree_chen_asl_measures.csv
* coree_chen_dwi_measures.csv
* coree_chen_rsfmri_yeobuckner131_interconn_corticocereb.csv
* coree_chen_rsfmri_yeobuckner131_interconn_wholebrain.csv
* coree_chen_rsfmri_yeobuckner131_withinconn

## Create Python environment
Use a python virtual environment manager to create an environment for the panpipelines 1.1.4 release. Options include `virtualenv`, `conda`, `micromamba` etc. We will use `virtualenv` in this example.

### Install `virtualenv` and prepare virtual environment
Install `virtualenv` in python environment:

```
module load python/3.11/3.11.4
pip install --user virtualenv
```

Create a virtual environment called `pan_april2025_env` in a location defined by `ENVLOC`

```
ENVNAME=pan_april2025_env
ENVLOC=/xdisk/trouard/$USER/PAN/april2025_repro/venvs
mkdir -p $ENVLOC
module load python/3.11/3.11.4
virtualenv -p python3 $ENVLOC/$ENVNAME
```

Activate environment and Install version 1.1.4 of PAN pipelines using `pip`
```
module load python/3.11/3.11.4
source $ENVLOC/$ENVNAME/bin/activate
pip install panpipelines==1.1.4
```

## Deployment Folder Structure
Create a root directory from which you will reproduce the analysis.

## Clone Panpipelines repository and copy folders
In a separate folder clone the Panpipelines repository and from the `april2025_PAN_Deployment` folder copy the folders   **atlas**,**batch_scripts** , **config**, **containers**, **external_scripts** and the run script `runpan.sh` to your root directory.

Obtain the weights for the tractseg container from its github page or alternatively Download `tractseg_home.zip` from `https://osf.io/fpbkn/files/osfstorage` to the root directory and unzip it.


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
│   ├── freesurfer_outputs_april.csv <br/>
│   ├── gm_model.json <br/>
│   ├── hml_ids_list_241231.csv <br/>
│   ├── license.txt <br/>
│   ├── pan.config.april2025 <br/>
│   ├── pan_eddyparams_cuda.json <br/>
│   ├── sessions.tsv <br/>
│   └── style.css <br/>
├── containers <br/>
├── external_scripts <br/>
│   └── amico <br/>
├── runpan.sh <br/>
├── tractseg_home <br/>

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


## Apptainer Provenance
Details of all the apptainers except 2 are provided in relevant references from the associated institutions. The other two apptainers  (`aacazxnat/panproc-minimal:0.2` and `aacazxnat/panproc-apps:0.1`) are custom made containers, the recipes for which are provided here https://github.com/MRIresearch/panproc-minimal (using v0.2 tag for this release) and https://github.com/MRIresearch/panproc-minimal/tree/main/panproc-apps respectively.


## Edit `pan.config.april2025`
If the above folder configuration is used then there should be no required changes in the the config file. If paths to containers and scripts are an issue then you may need to change this here.


## Freesurfer license
Update the provided freesurfer license in `./config/license.txt` with your personal license if you have one. The pipeline will run with the existing license but it is good practice to use your own license. You can get a license from the Freesurfer main website.

## Edit runpan.sh
Add commands required to instantiate your python environment e.g. module load env, conda activate env etc.

Change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`

Change `PKG_DIR` to point to the directory that contains the pipelines package:
`PKG_DIR=[Path to]/PANpipelines/src`. This will be in your conda or python or virtual env environment if you installed PANpipelines using `pip`. If you are using the code directly from the repository then this will be the path to the cloned repository.

If you have decided not to install the PANpipelines package but have downloaded the repository then add the path to the `src` folder in the `PYTHONPATH` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

## Edit  slurm templates in ./batch_script
Edit `group_template.pbs` and `participant_template.pbs` and add commands required to instantiate your python environment e.g. module load env, conda activate env etc.

Also change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`

If you have decided not to install the PANpipelines package but have downloaded the repository then you may need to add the path to the `src` folder in the `PYTHONPATH` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

## Edit  batch_scripts/headers
Go through each of the different slurm headers to adjust times and credentials as necessary. These are referenced in the config entries as `SLURM_CPU_HEADER` and `SLURM_GPU_HEADER` as required.

##  Deploy
run as `./runpan.sh`. The script is currently set to run a selection of 10 subjects. To run all subjects then use "ALL_SUBJECTS" in the participant variable. Please note that some SLURM configurations place limits on the numbers of jobs that can be run. Each subject will require about 40 jobs for the single subject pipeline. And there are 11 group jobs. So for N subjects a total of `40*N + 11` Jobs will be required. To run all the subjects you may need to run them in batches of Nmax depending on your SLURM constraints and pass different participants to run using the setting `SESSIONSFILE="--sessions_file $CURRDIR/config/sessions.tsv"` with a different `sessions.tsv` file for each batch. 


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.

if you see this error `ImportError: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips  26 Jan 2017'. See: https://github.com/urllib3/urllib3/issues/2168` and you are using `Python 3.7 - 3.9` on the HPC then downgrade `urllib3` as follows `pip install urllib==1.25.9` 

# General HPC Deployment
As described in the main README, one of the current limitations of the pipeline is the fact that it has been tested on **SLURM** environments in which singularity containers are automatically bound by the system administrator to disk locations on which users manage their data. There is however support for the use of the `-B` parameter  to map output locations to their respective locations within the singularity image. This functionality will attempt to automatically translate all host location parameters in a command call to their container locations. This has not been extensively tested and so should be used with caution.
