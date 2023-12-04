# PANpipelines deployment

## Prepare Virtual Environment
It is advisable to create a virtual python environment to run the PAN pipelines An example using a `conda` virtual environment is shown as an example. It is recommended to use a python version of `3.8.2` or greater.
```
conda create -n pandev python=3.10.13
```

if you would like to create your virtual environment in a specific folder location then use the `-p` prefix parameter instead of the `-n` name parameter as follows:
```
conda create -p /path/to/pandev python=3.10.13
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
pip install -U --user panpipelines
```

### Use this repository and perform:
```
cd PANpipelines
pip install -e ./
```

### Use the python source files in the repository without installing PANpipelines
With this option you will need to manually install the required python packages as follows:

```
pip install --user nipype==1.8.6
pip install --user numpy==1.24.4
pip install --user nibabel==5.1.0
pip install --user nilearn==0.10.2
pip install --user pandas==2.0.3
pip install --user xnat==0.5.2
pip install --user pydicom==2.4.3
pip install --user templateflow==23.1.0
pip install --user nitransforms==23.0.1
pip install --user pybids==0.16.3
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

Change `PWD` to point to the root directory of this deployment directory
`"PWD": "/path/to/newdeployment",`

Change `PKG_DIR` to point to the directory that contains the pipelines package:
`"PKG_DIR": "/Path/to/PANpipelines/src"`

Change 'XNAT_HOST' to the XNAT URL

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

If you have decided not to install the PANpipelines package but have downloaded the repository then add the path to the `src` folder in the `PYTHONPATh` environmental variable as follows:
```
export PYTHONPATH=${PKG_DIR}:$PYTHONPATH
```

### slurm templates in ./batch_script
Edit `group_template.pbs` and `participant_template.pbs` and change the call to PYTHON depending on how it is invoked in your environment. Some environments require Python version 3 to be invoked as `python3`. In that case set `PYTHON=python3`
### batch_scripts/headers
Go through each of the different slurm headers to adjust times and credentials as necessary. These are referenced in the config entries as `SLURM_CPU_HEADER` and `SLURM_GPU_HEADER` as required.

### Deploy
run as `./run_pan_slurm.sh`


## Troubleshooting
Most problems can be avoided by creating a clean new python environment using `conda` or `virtualenv`. If an existing python environment is used then package interactions and conflicts will unfortunately have to be handled manually and steps to resolve these will be unique to each environment in question.