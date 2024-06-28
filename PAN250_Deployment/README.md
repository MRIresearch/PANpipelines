# PANpipelines Deployment for PAN 250 Release
These notes provide guidelines for reproducing the PANpipelines for the PAN 250 Release in a SLURM-based HPC envrionment. Specific notes are provided in the section **U of A HPC Deployment** for deploying these pipelines in the University of Arizona's Puma HPC environment. General notes for deployment are provided in **General HPC Deployment** section in the `README.md` in the `PANPippelines/deployment` folder.

# University of Arizona HPC Deployment

## Create personal deployment directory
Clone the PANpipelines repository and copy the deployment folder to your own workspace as follows:
```
cd /xdisk/ryant/$USER
git clone https://github.com/MRIresearch/PANpipelines.git
cp -R /xdisk/ryant/$USER/PANpipelines/PAN250_Deployment /xdisk/ryant/$USER/PAN250_Deployment
```

## Load Python Environment and Prepare Virtual Environment
The most convenient approach to deploying these pipelines in the U of A's HPC Cluster is to use the preinstalled python module and we will use `virtualenv` to manage our python dependenices.


```
module load python/3.11/3.11.4
pip install --user virtualenv
```

Create a virtual environment called `pan250_env`

```
mkdir /xdisk/ryant/$USER/PAN250_Deployment/venvs
module load python/3.11/3.11.4
virtualenv -p python3 /xdisk/ryant/$USER/PAN250_Deployment/venvs/pan250_env
```

Activate environment and Install the latest version of PAN pipelines using `pip`
```
module load python/3.11/3.11.4
source /xdisk/ryant/$USER/PAN250_Deployment/venvs/pan250_env/bin/activate
pip install -U panpipelines
```

## Deployment Folder Structure
Each Analysis utilizes the following three folders **config**, **atlas** and **batch_scripts** and a run script `*_run_pan250_*.sh`. There is a default copy of these fodlers and files in the deployment folder.

Individual folders named **YYYYMMDD** contain specific updates to the generic files and folders above for a specific analysis run. So for example **20240530** contains updates to the **config** folder that should be used instead of the generic version to recreate the results available in **results**. 

There is a limitation to the number of slurm jobs that an individual can invoke at the same time on the HPC (approx 1000 jobs) and so in practical terms jobs have to be broken up into smaller batches. For the example of **20240530** the first batch of jobs invoked by `001_run_pan250_aslproc.sh` will need to complete before the second batch `002_run_pan250_aslproc.sh` can be run.

## Edit pan250.config

In the configuration file `./config/pan250.config` make the following changes:

Change `XNAT_HOST` to the XNAT URL i.e. `https://....`

Currently a central data location as defined by `DATA_DIR` is being used to avoid duplication of data across individual users. If you prefer to isolate data for your pipelines from other users then you can change this location to another one.

## Edit  credentials and change access permissions
Change the username and password in `./config/credentials/credentials.json` to your XNAT credentials.

Change access permissions on `credentials.json` to prevent unauthorized access. Using `chmod 400` on `credentials.json` should be the most conservative way to achieve this. You will need to set the folder `./config/credentials/` most conservatively to `500` if you also want to restrict access to the folder. Anything more conservative may prevent access to the file by the program.

## Freesurfer license
Update the provided freesurfer license in `./config/license.txt` with your personal licens if you have one. The pipeline will run with the existing license but it is good practice to use your own license. You can get a license from the Freesurfer main website.

## Edit run_pan250.sh
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
run as `./run_pan250.sh`.

On your first run please allow a few minutes for the PAN participation information to be obtained for all the projects from the server.


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.

if you see this error `ImportError: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips  26 Jan 2017'. See: https://github.com/urllib3/urllib3/issues/2168` and you are using `Python 3.7 - 3.9` on the HPC then downgrade `urllib3` as follows `pip install urllib==1.25.9` 

# General HPC Deployment
As described in the main README, one of the current limitations of the pipeline is the fact that it is only optimised for **SLURM** environments in which singularity containers are automatically bound by the system administrator to disk locations on which users manage their data. This means that the `-B` parameter is not required to map output locations to their respective locations within the singularity image.  If the latter is not the case then users will need to run their deployments in the `/tmp` directory as this is automatically bound by singularity. We hope to eventually enable this pipeline to work in other scenarios that users may be facing e.g. Docker environments and more restrictive singularity environments.

Several pipelines rely on the image `aacazxnat/panproc-minimal:0.2` which is defined here https://github.com/MRIresearch/panproc-minimal. See the section **Building singularity images from Docker Images** in main READMe for information on how to convert your docker images into singularity images. Users may want to customize this image so that it works better on their HPC systems.