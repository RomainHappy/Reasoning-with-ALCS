# BEACS

## Installation

Python 3.x has to be installed to use BEACS. 
We suggest you to use *conda* or *miniconda*.

Then, you have to create a conda environment according to the environment file included in the repository :

` conda env create -f environment.yml `

*This file needs to be updated so that you won't get errors during the installation -> WIP*

## License

This work is dual-licensed under MPL-2.0 and MIT.

The pieces of code that have been developed by the owner of this project are licensed under MPL-2.0.

All files under that license have a boilerplate notice at the top of the files.

All other files that don't have this boilerplate are licensed under the MIT license and come from :

    - https://github.com/ParrotPrediction/pyalcs
    - https://github.com/ParrotPrediction/openai-envs

## How to set up experiments with Ray

Be sure to have Ray installed ;)

Currently only available with :
- MazeBenchBeacs_Ray.ipynb

On Local Mode :
1. Open the desired jupyter-notebook that has Ray.
2. Comment or delete `ray.init(address='auto', _redis_password='5241590000000000')` if present.
3. Uncomment or write `ray.init(num_cpus=NB_OF_PROCESSES, ignore_reinit_error=True)` if not present.
4. Start running the code of he jupyter-notebook.

On Remote Mode :
1. Start a first ssh tunnel towards your server : `ssh -L <port>:<addressip>:<port jupyter> <user>@<addressip>`
2. Launch a Jupyter server and be sure you can access it through your tunnel. Think about using `jupyter-notebook --port <port jupyter> --no-browser` or updating the config file.
3. Launch a Ray server with : `ray start --head --dashboard-host "0.0.0.0"`. Be carefull about where you start the server, otherwise you'll need to change some lines of code in the import part of the ray remote function.
4. Start a second ssh tunnel towards your ray dashbord : `ssh -L <port>:<addressip>:8265 <user>@<addressip>`. 8265 is the default dashboard ray port and can be changed if needed with *--dashboard-port* option in the previous step.
5. Open the desired jupyter-notebook that has Ray.
6. Uncomment or write `ray.init(address='auto', _redis_password='5241590000000000')` if not present. *_redis_password* can be another one and is given when the ray server is started.
7. Comment or delete `ray.init(num_cpus=NB_OF_PROCESSES, ignore_reinit_error=True)` if present.
8. Start running the code of he jupyter-notebook.
