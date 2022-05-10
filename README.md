![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/wiki/os-simopt/wrftamer/python-coverage-comment-action-badge.json) [![pytest](https://github.com/os-simopt/wrftamer/actions/workflows/python-pytest.yml/badge.svg)](https://github.com/os-simopt/wrftamer/actions/workflows/python-pytest.yml) ![License badge](https://img.shields.io/github/license/os-simopt/wrftamer)

# WRFtamer
WRFtamer is a tool to organize WRF simulations. This includes organizing experiments into projects, creating simulations, running WPS, postprocessing data and archiving completed runs. This tool also provides an overview on how long a simulation runs and how much disk space it takes. 
The programm can be used from the command line and using a graphical user interface (GUI).
WRFtamer is designed to run WRF with em_real. Is is able to create sumbit-scripts for the cluster, but only for the SLURM job scheduler. 

## Requirements
This repository has been tested with python 3.7.12
### External python modules
See requirements.txt
 
## Installation
It can be installed using pip
```bash
pip install wrftamer
```
or conda

```bash
conda install -c os-simopt wrftamer
```

### Optional python modules
The Cartopy package is required to display maps of your data. If you want to use these features, you need to install this package manually.

**Info:** The pip installer for cartopy does not work (as of 26.04.2022).
It is required to install cartopy using conda or mamba before wrftamer can be installed.



## First Steps and documentation

To get started with WRFtamer, got to
[first steps](https://wrftamer.readthedocs.io/en/latest/getting_started/#first-steps-to-use-wrftamer)

The full documentation is available [here](https://wrftamer.readthedocs.io/en/latest/)

## Owners
Martin Felder, Linda Menger, Daniel Leukauf
## Licence
MIT
