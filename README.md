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
The current pipeline is currently optimised for **SLURM** environments in which singularity containers are automatically bound by the system administrator to disk locations on which users manage their data. This means that the `-B` parameter is not required to map output locations to their respective locations within the singularity image.  If the latter is not the case then users will need to run their deployments in the `/tmp` directory as this is automatically bound by singularity. We hope to eventually enable this pipeline to work in other scenarios that users may be facing e.g. Docker environments and more restrictive singularity environments. 
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

### Unsorted dump of config settings
Following below is a dump of config settings which will be reviewed and described better above:

```
"SESSION_LABEL": ["ALL_SESSIONS"]
      "PROCESSING_ENVIRONMENT": "slurm", 
      "ARRAY_INDEX": "SLURM_ARRAY_TASK_ID",
      "ENV_PROCS": "SLURM_CPUS_ON_NODE",
      "BIDSAPP_THREADS": "10",
      "BIDSAPP_MEMORY": "50000",
      "ANALYSIS_LEVEL": "participant",
      "ANALYSIS_NODE": "cpu",
      "PROC_DIR": "<PWD>",
      "CREDENTIALS": "<PROC_DIR>/config/credentials/credentials.json",
      "CONFIG": "<PROC_DIR>/config/panpipeconfig.json",
      "PIPELINE_DIR": "<PROC_DIR>/pan_output",
      "FSLICENSE": "<PROC_DIR>/config/license.txt",
      "DATA_DIR": "/xdisk/ryant/chidiugonna/PAN250_Data",
      "PARTICIPANTS_FILE": "<DATA_DIR>/tsv/participants.tsv",
      "BIDS_DIR": "<DATA_DIR>/BIDS",
      "LOCK_DIR": "<DATA_DIR>/datalocks",
      "SESSIONS_FILE": "<DATA_DIR>/tsv/sessions.tsv",
      "PAN_CONTAINER": "/groups/ryant/PANapps/panprocminimal-v0.1.sif",
      "NEURO_CONTAINER": "/groups/ryant/PANapps/panprocminimal-v0.1.sif",
      "CONTAINER": "<PAN_CONTAINER>",
      "CONTAINER_RUN_OPTIONS": "singularity run --cleanenv --no-home",
      "CONTAINER_PRERUN" : "--home", 
      "QSIPREP_CONTAINER": "/groups/ryant/PANapps/qsiprep-0.19.0.sif",
      "QSIPREP_CONTAINER_RUN_OPTIONS": "singularity exec --cleanenv --no-home",
      "QSIPREP_CONTAINER_PRERUN" : "/usr/local/miniconda/bin/qsiprep", 
      "FMRIPREP_CONTAINER": "/groups/ryant/PANapps/fmriprep-23.2.0.sif",
      "FMRIPREP_CONTAINER_RUN_OPTIONS": "singularity run --cleanenv --no-home -B <FMRIWORK>:/work -B <FMRIOUTPUT>:/out",
      "FMRIPREP_CONTAINER_PRERUN" : " ",
      "ASLPREP_CONTAINER": "/groups/ryant/PANapps/aslprep_0.5.1.sif",
      "ASLPREP_CONTAINER_RUN_OPTIONS": "<CONTAINER_RUN_OPTIONS>",
      "ASLPREP_CONTAINER_PRERUN" : " ",
      "LST_CONTAINER": "/groups/ryant/PANapps/nklab-spmjobman.sif",
      "LST_CONTAINER_RUN_OPTIONS": "singularity run --cleanenv",
      "LST_CONTAINER_PRERUN" : "--homedir=<LST_OUTPUT_DIR>",
      "ANTS_CONTAINER": "<PAN_CONTAINER>",
      "BASIL_CONTAINER": "<PAN_CONTAINER>",
      "FREESURFER_CONTAINER": "<PAN_CONTAINER>",
      "FSL_CONTAINER": "<PAN_CONTAINER>",
      "MRTRIX_CONTAINER": "<PAN_CONTAINER>",
      "WB_CONTAINER": "<PAN_CONTAINER>",
      "XNAT_HOST": "https://aacazxnat.arizona.edu",
      "TEMPLATEFLOW_HOME": "<PROC_DIR>/TemplateFlow",
      "SLURM_SCRIPT_DIR": "<PIPELINE_DIR>/<PIPELINE>/0_slurm_submit",
      "SLURM_DEPENDENCY": "afterany",
      "SLURM_HEADER_DIR": "<PROC_DIR>/batch_scripts/headers",
      "SLURM_TEMPLATE_DIR": "<PROC_DIR>/batch_scripts",
      "SLURM_PARTICIPANT_TEMPLATE": "<SLURM_TEMPLATE_DIR>/participant_template.pbs",
      "SLURM_GROUP_TEMPLATE": "<SLURM_TEMPLATE_DIR>/group_template.pbs",
      "SLURM_CPU_HEADER": "<SLURM_HEADER_DIR>/slurm_cpu_highpri.pbs",
      "SLURM_GPU_HEADER": "<SLURM_HEADER_DIR>/slurm_gpu.pbs"


    "fmriprep_panpipeline":
    {
      "USE_MEGRE_FMAP": ["HML0096_SESSION002","HML0097"]
    },

    "qsiprep_panpipeline":
    {
      "EDDY_CONFIG": "<PROC_DIR>/config/pan250_eddyparams.json",
      "OUTPUT_RES": "2.0"
    },

    "noddi_panpipeline":
    {
      "DEPENDENCY": "qsiprep_panpipeline",
      "RECON_TYPE": "amico_noddi",
      "QSIPREP_OUTPUT_DIR" : "<DEPENDENCY_DIR>/qsiprep_node/qsiprep",
      "OUTPUT_RES": "2.0"
    },

```    "noddimeasures_xtract_2mm":
    {
      "PIPELINE_CLASS": "roiextract_panpipeline",
      "DEPENDENCY": ["noddi_panpipeline","qsiprep_panpipeline"],
      "SLURM_CPU_HEADER": "<SLURM_HEADER_DIR>/slurm_cpu_highpri_tiny.pbs",
      "ATLAS_NAME": "xtract",
      "ATLAS_FILE": "<PROC_DIR>/atlas/XTRACT/MNI152NLin6Asym/tpl-MNI152NLin6Asym_res-02_atlas-XTRACT_dseg.nii.gz",
      "ATLAS_INDEX": "<PROC_DIR>/atlas/XTRACT/res-02_atlas-XTRACT_dseg.tsv",
      "ATLAS_TRANSFORM_MAT": ["from-MNI152NLin6Asym_to-MNI152NLin2009cAsym_res-2"],
      "MEASURES_TEMPLATE": "<DEPENDENCY1_DIR>/noddi_node/qsirecon/sub-<PARTICIPANT_LABEL>/ses-*/dwi/*_desc-preproc_desc-*.nii.gz",
      "MEASURES_TRANSFORM_MAT": ["<DEPENDENCY2_DIR>/qsiprep_node/qsiprep/sub-<PARTICIPANT_LABEL>/anat/sub-<PARTICIPANT_LABEL>_from-T1w_to-MNI152NLin2009cAsym_mode-image_xfm.h5"],
      "MEASURES_TRANSFORM_REF": "MNI152NLin2009cAsym_res-2",
      "ATLAS_TRANSFORM_REF": "MNI152NLin2009cAsym_res-2"
    },
   
       "basil_voxel_sdcflow":
    {
      "PIPELINE_CLASS": "basil_panpipeline",
      "SDCFLOWS_CONTAINER_TO_USE": "SDCFLOWS_CONTAINER",
      "SLURM_CPU_HEADER": "<SLURM_HEADER_DIR>/slurm_cpu_highpri_long.pbs",
      "SDCFLOWS_CONTAINER": "/groups/ryant/PANapps/fmriprep-23.2.0.sif",
      "SDCFLOWS_CONTAINER_RUN_OPTIONS": "singularity exec ",
      "SDCFLOWS_CONTAINER_PRERUN" : " ",
      "ANALYSIS_NODE": "cpu",
      "FIELDMAP_TYPE" : {
          "acq-prod" : "sdcflows_preproc",
          "acq-pcasl" : "sdcflows_preproc",
          "acq-plusM0" : "sdcflows_preproc"
      },
      "SDCFLOWS_FIELDMAP_DIR" : {
           "acq-prod" : "<WORKFLOW_DIR>/sdcflows/fmap",
           "acq-pcasl" : "<WORKFLOW_DIR>/sdcflows/fmap",
           "acq-plusM0" : "<WORKFLOW_DIR>/sdcflows/fmap"
      },
      "ASL_ECHOSPACING" : {
           "acq-prod" : "0.0005",
           "acq-pcasl" : "0.0002371",
           "acq-plusM0" : "0.0005"
      },
      "ASLCONTEXT" : {
        "acq-prod" : "control:label",
        "acq-pcasl" : "control:label",
        "acq-plusM0" : "m0scan:control:label"
      },
      "CMETHOD_OPTS" : {
        "acq-prod" : "voxel",
        "acq-pcasl" : "voxel",
        "acq-plusM0" : "voxel"
      }
    }

         "basilmeasures_tissue":
    {
      "PIPELINE_CLASS": "roiextract_panpipeline",
      "DEPENDENCY": "basil_voxel_sdcflow",
      "SLURM_CPU_HEADER": "<SLURM_HEADER_DIR>/slurm_cpu_highpri_small.pbs",
      "ATLAS_NAME": "brainseg_t1",
      "NEWATLAS_TEMPLATE": ["<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1_fast_pve_0.nii.gz","<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1_fast_pve_1.nii.gz","<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1_fast_pve_2.nii.gz"],
      "NEWATLAS_INDEX": [ "csf", "gm", "wm"],
      "NEWATLAS_TRANSFORM_REF": "MNI152NLin2009cAsym_res-2",
      "NEWATLAS_TRANSFORM_MAT": [["<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1_to_MNI_nonlin_field.nii.gz:FSL:<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1.nii.gz","from-MNI152NLin6Asym_to-MNI152NLin2009cAsym"],
      ["<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1_to_MNI_nonlin_field.nii.gz:FSL:<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1.nii.gz","from-MNI152NLin6Asym_to-MNI152NLin2009cAsym"],
      ["<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1_to_MNI_nonlin_field.nii.gz:FSL:<DEPENDENCY1_DIR>/fslanat_node/<PARTICIPANT_LABEL>_struct.anat/T1.nii.gz","from-MNI152NLin6Asym_to-MNI152NLin2009cAsym"]],
      "MEASURES_TEMPLATE": "<DEPENDENCY1_DIR>/basil_node/basiloutput/std_space/*calib*.nii.gz",
      "MEASURES_TRANSFORM_MAT": ["from-MNI152NLin6Asym_to-MNI152NLin2009cAsym_res-2"],
      "MEASURES_TRANSFORM_REF": "MNI152NLin2009cAsym_res-2"
    },