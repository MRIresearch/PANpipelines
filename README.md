# PANpipelines
---
This repository contains all the necessary scripts for reproducing the steps taken to preprocess and analyze MRI data collected during the Precision Aging Network (PAN) project.

## The panpipelines package
The PAN Pipelines use a set of python modules packaged under the main `panpipelines` package to run all the preprocessing and analysis workflows which are based on NiPype. 

## Installation
It is recommended that a python environment manager like `conda` or `virtualenv` is used to install the **panpipelines** package. Assuming you have created a conda environment called `panpython` then the package can be installed as follows:

```
conda activate panpython
pip install panpipelines
```
## Deployment
For an example of using the package to process MRI data please refer to the `./deployment` folder. All the necessary parameters for running the pipelines are described in a **config** file in the `./config` subdirectory which is passed as a parameter to the main module `pan_processing.py`. In the example provided this file is name `panpipeconfig_slurm.config`.

