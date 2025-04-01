# Reproducing April 2025 MRI PAN Measures
The following instructions can be followed to replicate the results provided as part of the April 2025 data release on a slurm-based HPC environment.

## Tables released

* coree_chen_anat_measures.csv
* coree_chen_asl_measures.csv
* coree_chen_dwi_measures.csv
* coree_chen_rsfmri_yeobuckner131_interconn_corticocereb.csv
* coree_chen_rsfmri_yeobuckner131_interconn_wholebrain.csv
* coree_chen_rsfmri_yeobuckner131_withinconn

## Create Python environment
Use a python virtual environment manager to create an environment for the panpipelines 1.1.2 release. Options include `virtualenv`, `conda`, `micromamba` etc. We will use `virtualenv` in this example.

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

Activate environment and Install version 1.1.2 of PAN pipelines using `pip`
```
module load python/3.11/3.11.4
source $ENVLOC/$ENVNAME/bin/activate
pip install panpipelines==1.1.2
```

## Deployment Folder Structure
Create a root directory from which you will reproduce the analysis.

Navigate to the root directory and from the main repository copy folders **config**, **atlas**,**tractseg_home** and **batch_scripts** and the run script `runpan.sh`.

Also copy the folder `PANpipelines/external_scripts/amico` to a folder called `external_scripts` in your root directory

├── atlas
│   ├── Arterial
│   ├── freesurfer_atlas
│   ├── tractseg
│   └── xcpd_custom_atlases
├── batch_scripts
│   ├── group_template.pbs
│   ├── headers
│   └── participant_template.pbs
├── config
│   ├── freesurfer_outputs_april.csv
│   ├── gm_model.json
│   ├── hml_ids_list_241231.csv
│   ├── license.txt
│   ├── pan.config.april2025
│   ├── pan_eddyparams_cuda.json
│   ├── sessions.tsv
│   └── style.css
├── external_scripts
│   └── amico
├── runpan.sh
├── tractseg_home

## Create associated Apptainers
The PAN pipelines rely on a number of apptainer images which are required to successfully run the pipelines. These are available as docker images which can be converted to singularity images. Provided is an example for panprocminimal-v0.2.sif

```
export APPTAINER_CACHEDIR=$PWD/singularitycache 
SINGNAME=panprocminimal-v0.2.sif
DOCKERURI=docker://aacazxnat/panproc-minimal:0.2
singularity build $SINGNAME $DOCKERURI
```

The following singularity images should be generated and stored in an accessible location on your file system for example `/rootdir/containers`

docker://aacazxnat/panproc-minimal:0.2 > panprocminimal-v0.2.sif
docker://pennbbl/qsiprep:0.21.4 > qsiprep-0.21.4.sif 
docker://nipreps/fmriprep:0.21.4 > fmriprep-24.1.1.sif
docker://wasserth/tractseg_container:master > tractseg.sif 
docker://pennlinc/xcp_d:0.10.5 > xcpd-0.10.5.sif
docker://aacazxnat/panproc-apps:0.1   > panapps.sif

## Edit `pan.config.april2025`

In the configuration file `./config/pan.config.april2025` correct the following container references with their file locations on your system.

```
"PAN_CONTAINER": "/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/panprocminimal-v0.2.sif",
"QSIPREP_CONTAINER": "/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/qsiprep-0.21.4.sif",
"FMRIPREP_CONTAINER": "/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/fmriprep-24.1.1.sif",
"TRACTSEG_CONTAINER": "/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/tractseg.sif",
"XCPD_CONTAINER": "/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/xcpd-0.10.5.sif",
```

The PANAPPS container is found further below the file on about line 673 in the amiconoddi-gm pipeline and also needs to be corrected.
```
"PANAPPS_CONTAINER": "/xdisk/trouard/chidiugonna/PAN/april2025_repro/containers/panapps.sif"
```

Also correct the entry for amiconoddi-gm's external script to point to the correct location

```
"SCRIPT_FILE" : "/xdisk/trouard/chidiugonna/PAN/april2025_repro/external_scripts/
```

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
run as `./runpan.sh`.


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.

if you see this error `ImportError: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips  26 Jan 2017'. See: https://github.com/urllib3/urllib3/issues/2168` and you are using `Python 3.7 - 3.9` on the HPC then downgrade `urllib3` as follows `pip install urllib==1.25.9` 

# General HPC Deployment
As described in the main README, one of the current limitations of the pipeline is the fact that it is only optimised for **SLURM** environments in which singularity containers are automatically bound by the system administrator to disk locations on which users manage their data. This means that the `-B` parameter is not required to map output locations to their respective locations within the singularity image.
