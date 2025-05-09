# PANpipelines
---
This repository contains all the necessary scripts for reproducing the steps taken to preprocess and analyze MRI data collected during the Precision Aging Network (PAN) project.

# The panpipelines package
The PAN Pipelines use a set of python modules packaged under the main `panpipelines` package to run all the preprocessing and analysis workflows which are based on NiPype. 

# Installation
It is recommended that a python environment manager like `conda` or `virtualenv` is used to install the **panpipelines** package. Assuming you have created a conda environment called `panpython` then the package can be installed as follows:

```
conda activate panpython
pip install panpipelines
```
# Current Limitations
The current pipeline is currently optimised for **SLURM** environments in which singularity containers are automatically bound by the system administrator to disk locations on which users manage their data. There is however support for the use of the `-B` parameter  in singularity to map output locations to their respective locations within the singularity. This functionality will attempt to automatically translate all host location parameters in a command call to their container locations. This has not been extensively tested and so should be used with caution.

By changing the `PROCESSING_ENVIRONMENT` parameter in the config file to `local` then pipelines will be run without being submitted to slurm using python's `multiprocessing` library. Docker containers can also be invoked instead of singularity images by using `docker run` instead of `singularity run` in the `*_CONTAINER_RUN_OPTIONS` parameter.

Several pipelines rely on the image `aacazxnat/panproc-minimal:0.2` which is defined here https://github.com/MRIresearch/panproc-minimal. See the section below **Building singularity images from Docker Images** for information on how to convert your docker images into singularity images.

# Building singularity images from Docker Images
The script below can be used to build a singularity image from a docker image. The script defines a location `$SINGULARITY_CACHEDIR` which is used to download the image layers. This can be set up in a location where there is a reasonable amount of disk space as the layers can be quite large in size. The docker image location is defined by `$DOCKERURI`. Once the singularity image `$SINGNAME` is built it can be moved to another location if desired.

```
#!/bin/bash
export SINGULARITY_CACHEDIR=$PWD/singularitycache
mkdir -p $SINGULARITY_CACHEDIR

SINGNAME=panprocminimal-v0.2.sif
DOCKERURI=docker://aacazxnat/panproc-minimal:0.2
singularity build $SINGNAME $DOCKERURI
```

# Deployment
For an example of using the package to process MRI data please refer to the `./deployment` folder. All the necessary parameters for running the pipelines are described in a **config** file in the `./config` subdirectory which is passed as a parameter to the main module `pan_processing.py`. In the example provided this file is named `panpipeconfig_slurm.config`. 

The scripts used to process data for the 1st 250 participants of the PAN project are available in `PAN250_Deployment`.

The scripts used to process data for the April 2025 Deployment of the PAN project are available in `april2025_PAN_Deploymnent`

# Running pan_processing.py
The pan processing pipelines are run by simply calling the `pan_processing.py` as described in the script `run_pan250.sh` in the `PAN250_Deployment` directory.

The following parameters are available:

`config_file` : The configuration file 

`--pipeline_outdir` : The ouput directory. This overrides `PIPELINE_DIR` in configuration file

`--participants_file` : The list of participants. This overrides `PARTICIPANTS_FILE` in configuration file. 

`--sessions_file` : The list of sessions. This overrides `SESSIONS_FILE` in configuration file.

`--pipelines` : List of pipelines to run. This overrides `PIPELINES` in configuration file. If let undefined then all pipelines are run.

`--pipeline_match` : Pattern to use to filter out pipelines that you want from the full list of pipelines. 

`--projects` : List of Projects to use for processing. If this is undefined then the PAN projects `"001_HML","002_HML","003_HML",and "004_HML"` are used.

`--participant_label` : Specify participants to process. This overrides `PARTICIPANT_LABEL`. Pass in `ALL_SUBJECTS` to process all subjects defined in the parricipants list.

`--participant_exclusions` : Specify participants to exclude from processing.

`--session_label` : Specify sessions to process. This overrides `SESSION_LABEL`. Pass in `ALL_SESSIONS` to process all sessions availabe to subjects defined in the parricipants list.


# Config file structure
The configuration file `pan250.config` drives how the processing occurs. It uses `json` format. The first entry is always called `"all_pipelines"` and this contains configuration details that are common to all pipelines. Individual pipelines can then be configured in the file. Any configuration details specified for an individual pipeline will override the common entry defined in the "all_pipelines" section.

## Lookup and direct parameters in the config file
Parameter values that are surrounded opening ad closing arrows e.g. `<PROC_DIR>` are lookup variables that are populated by the actual direct definitoons of these variables. For example below:

```
"PROC_DIR" : "/xdisk/nkchen/chidigonna",
"DATA_DIR" : "<PROC_DIR>/data
```
would mean that `DATA_DIR` evaluates to `/xdisk/nkchen/chidigonna/data`. Without the surrounding arrows then it would evaluate to `PROC_DIR/data`

While there is some logic to sort parameters so that lookup variables are evaluated correctly regardless of order of definiton this has not been completelely tested and may fail in complex scenarios. It is advised that were possible any definitions that are required by downstream lookup variables are defined early and in the `all_pipelines` section where possible.

## Configuration entry examples for "all_pipelines"
| Key      | Description     | Example         | Default Value if undefined |
| -------- | --------------- | ----------------| ---------- |
| BIDS_SOURCE  | Data is to be downloaded from XNAT HOST, FTP or already exists locally | "BIDS_SOURCE" : "XNAT" | "LOCAL" |
| FORCE_BIDS_DOWNLOAD | Always download subject data from source even if the data already exists locally | "FORCE_BIDS_DOWNLOAD" : "Y" | "N" |


## Configuration entry examples at pipeline level
| Key      | Description     | Example         | Default Value if undefined |
| -------- | --------------- | ----------------| ---------- |
| PIPELINE_CLASS  | The pipeline type that the defined pipeline belongs to | "PIPELINE_CLASS" : "fmriprep_panpipeline" | N/A |
| PIPELINE_DIR | The parent directory for pipeline outputs. This is overwritten by the `--pipeline_outdir` parameter of `pan_processing.py` | "PIPELINE_DIR " : "/path/to/pipeline_output_directory" | N/A |

## Implicit Configuration entries
There are a number of configuration entries that are implicitly set by the software which in general are better left alone though there might be fringe use cases where it is helpful to overwrite. 

| Key      | Description     | Example         | Default Value if undefined |
| -------- | --------------- | ----------------| ---------- |
| PWD  | The working directory from which the shell script that invokes the python package is called. This can be overwritten to rerun processing located in another directory different from the startup script. | "CWD" : "path/to/new/working/directory" | N/A |
| PKG_DIR | The python package directory that is parent directory to the panpipelines source. This can be overwritten to use a different panpipeline package that is installed separate from the panprocessing.py module. It is hard to see a reason for this though.   | "PKG_DIR" : "/path/to/package" | N/A |

