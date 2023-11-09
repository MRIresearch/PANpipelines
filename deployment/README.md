## Testing PANpipelines Deployment using this Repository


### Create personal deployment directory
copy this deployment to your own workspace

### config/panpipeconfig_slurm.config

In the configuration file `./config/panpipeconfig_slurm.config` make the following changes:

Change `PWD` to point to the root directory of this deployment directory
`"PWD": "[Path to]/PANpipelines/deployment",`

Change `PKG_DIR` to point to the directory that contains the pipelines package:
"PKG_DIR": "[Path to]/PANpipelines/src"

Change 'XNAT_HOST' to the XNAT URL

### credentials
Change the username and password in `./config/credentials/credentials.json` to your XNAT credentials.

### Freesurfer license
Update the provided freesurfer license in `./config/license.txt` with your personal license.

### run_pan_slurm.sh

Change `PKG_DIR` to point to the directory that contains the pipelines package:
PKG_DIR=[Path to]/PANpipelines/src


### batch_scripts/headers
Go through each of the different slurm headers to adjust times and credentials as necessary.

### Deploy
run as `./run_pan_slurm.sh`