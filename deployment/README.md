# PANpipelines deployment

## Prepare Environment

Provided below are the python packages required to use the PANpipelines using `conda` as an example.
```
conda create -n pandev python=3.10.13
pip install nipype==1.8.6
pip install numpy==1.26.1
pip install nibabel==5.1.0"
pip install pydicom==2.4.3
pip install pybids==0.16.3
pip install pandas==2.1.2
pip install nilearn==0.10.2
pip install nitransforms==23.0.1
pip install templateflow==23.1.0
pip install xnat==0.5.2
```
With `conda` the pythin environment can be instantiated as follows:
```
conda activate pandev
```



## Install PAN pipelines
There are two options here - either to use PyPI package using:

```
pip install -U panpipelines
```

or use this repository and perform:
```
cd PANpipelines
pip install -e ./
```

## Testing PANpipelines Deployment 

### Create personal deployment directory
Copy the deployment folder to your own workspace

### config/panpipeconfig_slurm.config

In the configuration file `./config/panpipeconfig_slurm.config` make the following changes:

Change `PWD` to point to the root directory of this deployment directory
`"PWD": "[Path to]/PANpipelines/deployment",`

Change `PKG_DIR` to point to the directory that contains the pipelines package:
`"PKG_DIR": "[Path to]/PANpipelines/src"`

Change 'XNAT_HOST' to the XNAT URL

### credentials
Change the username and password in `./config/credentials/credentials.json` to your XNAT credentials.

Change access permissions on `credentials.json` to prevent unauthorized access. Using `chmod 400` on `credentials.json` should be the most conservative way to achieve this. You will need to set the folder ./config/credentials/ most conservatively to 500 if you also want to restrict access to the folder. Anything more conservative may prevent access to the file by the program.

### Freesurfer license
Update the provided freesurfer license in `./config/license.txt` with your personal license.

### run_pan_slurm.sh

Change `PKG_DIR` to point to the directory that contains the pipelines package:
`PKG_DIR=[Path to]/PANpipelines/src`


### batch_scripts/headers
Go through each of the different slurm headers to adjust times and credentials as necessary.

### Deploy
run as `./run_pan_slurm.sh`