# PANpipelines Deployment
These notes provide guidelines for reproducing the PANpipelines in a SLURM-based HPC envrionment. Specific notes are provided in the section **U of A HPC Deployment** for deploying these pipelines in the University of Arizona's Puma HPC environment. General notes for deployment are provided in **General HPC Deployment**.

# University of Arizona HPC Deployment
## Load Python Environment and Prepare Virtual Environment
The most convenient approach to deploying these pipelines in the U of A's HPC Cluster is to use the preinstalled python module and we will use `virtualenv` to manage our python dependenices.


```
module load python/3.11/3.11.4
pip install --user virtualenv
```

Create a virtual environment called `panvenv`

```
mkdir /xdisk/ryant/$USER/venvs
virtualenv -p python3 /xdisk/ryant/[USERNAME]/venvs/panvenv
```

Activate environment and Install the latest version of PAN pipelines using `pip`
```
module load python/3.11/3.11.4
source /xdisk/ryant/$USER/venvs/panvenv/bin/activate
pip install -U panpipelines
```

## Create personal deployment directory
Clone the PANpipelines repsoitory and copy the deployment folder to your own workspace as follows:
```
cd /xdisk/ryant/$USER
git clone https://github.com/MRIresearch/PANpipelines.git
cp -R /xdisk/ryant/$USER/PANpipelines/deployment /xdisk/ryant/$USER/pandeployment
```


## Edit panpipeconfig_slurm.config

In the configuration file `./config/panpipeconfig_slurm.config` make the following changes:

Change `XNAT_HOST` to the XNAT URL i.e. `https://....`

Currently a central data location as defined by `DATA_DIR` is being used to avoid duplication of data across individual users. If you prefer to isolate data for your pipelines from other users then you can change this location to another one.

## Edit  credentials and change access permissions
Change the username and password in `./config/credentials/credentials.json` to your XNAT credentials.

Change access permissions on `credentials.json` to prevent unauthorized access. Using `chmod 400` on `credentials.json` should be the most conservative way to achieve this. You will need to set the folder `./config/credentials/` most conservatively to `500` if you also want to restrict access to the folder. Anything more conservative may prevent access to the file by the program.

## Freesurfer license
Update the provided freesurfer license in `./config/license.txt` with your personal licens if you have one. The pipeline will run with the existing license but it is good practice to use your own license. You can get a license from the Freesurfer main website.

## Edit run_pan_slurm.sh
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
run as `./run_pan_slurm.sh`.

On your first run please allow a few minutes for the PAN participation information to be obtained for all the projects from the server.


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.

--- 
# General HPC Deployment
## Prepare Virtual Environment
It is advisable to create a virtual python environment to run the PAN pipelines An example using a `conda` virtual environment is shown below however `virtualenv` as demonstrated above could also be used. It is recommended to use a python version of `3.9` or greater.
```
conda create -n pandev python=3.11.4
```

if you would like to create your virtual environment in a specific folder location then use the `-p` prefix parameter instead of the `-n` name parameter as follows:
```
conda create -p /path/to/pandev python=3.11.4
```

With `conda` the python environment can be instantiated as follows depending on if the environment was created with the `-n` or the `p` parameter:
```
conda activate pandev
conda activate /path/to/pandev

```

## Install PAN pipelines
There are three options here:

### Use the PyPI package using:

```
pip install -U panpipelines
```

### Clone this repository and perform:
```
cd PANpipelines
pip install -e ./
```

### Use the python source files in the repository without installing PANpipelines
With this option you will need to manually install the required python packages as follows:

```
pip install nipype==1.8.6
pip install numpy==1.26.3
pip install nibabel==5.2.0
pip install nilearn==0.10.2
pip install pandas==2.1.4
pip install xnat==0.5.3
pip install pydicom==2.4.4
pip install templateflow==23.1.0
pip install nitransforms==23.0.1
pip install pybids==0.16.4
pip install scipy==1.11.4
```


and use the `PYTHONPATH` environmental variable.

In the file `run_pan_slurm.sh`, add the path to the `src` folder as follows:
`export PYTHONPATH=/path/to/PANpipelines/src:$PYTHONPATH`.

This is covered in the next section **Testing PANpipelines Deployment**


## Testing PANpipelines Deployment 

### Create personal deployment directory
Copy the deployment folder to your own workspace as follows:
```
cp -R /path/to/PANpipelines/deployment /path/to/newdeployment
```

### config/panpipeconfig_slurm.config

In the configuration file `./config/panpipeconfig_slurm.config` make the following changes:

Change `XNAT_HOST` to the XNAT URL i.e. `https://....`

### credentials
Change the username and password in `./config/credentials/credentials.json` to your XNAT credentials.

Change access permissions on `credentials.json` to prevent unauthorized access. Using `chmod 400` on `credentials.json` should be the most conservative way to achieve this. You will need to set the folder `./config/credentials/` most conservatively to `500` if you also want to restrict access to the folder. Anything more conservative may prevent access to the file by the program.

### Freesurfer license
Update the provided freesurfer license in `./config/license.txt` with your personal license.

### run_pan_slurm.sh
Add commands required to instantiate your python environment e.g. module load env, conda activate env etc.

Change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`

Change `PKG_DIR` to point to the directory that contains the pipelines package:
`PKG_DIR=[Path to]/PANpipelines/src`

If you have decided not to install the PANpipelines package but have downloaded the repository then add the path to the `src` folder in the `PYTHONPATH` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

### slurm templates in ./batch_script
Edit `group_template.pbs` and `participant_template.pbs` and add commands required to instantiate your python environment e.g. module load env, conda activate env etc.

Also change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`

If you have decided not to install the PANpipelines package but have downloaded the repository then you may need to add the path to the `src` folder in the `PYTHONPATH` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

### batch_scripts/headers
Go through each of the different slurm headers to adjust times and credentials as necessary. These are referenced in the config entries as `SLURM_CPU_HEADER` and `SLURM_GPU_HEADER` as required.

### Deploy
run as `./run_pan_slurm.sh`.

On your first run please allow a few minutes for the PAN participation information to be obtained for all the projects from the server.


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.

if you see this error `ImportError: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips  26 Jan 2017'. See: https://github.com/urllib3/urllib3/issues/2168` and you are using `Python 3.7 - 3.9` on the HPC then downgrade `urllib3` as follows `pip install urllib==1.25.9` 