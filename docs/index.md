# Welcome to WRFtamer

<img 
src="img/logo.png"
alt="WRFtamer"
style="float: left; margin-right: 15px;"
/>


Runing WPS and WRF could be done by hand, but this includes some repetetieve and cumbersome
tasks including:

- compiling WPS and WRF
- linking NWP data
- linking Vtable
- modify namelist.wps and namelist.input
- running geogrid.exe, ungrid.exe, metgrid.exe and real.exe
- running wrf.exe
- postprocessing
- management of multiple simulations.

Since this process is prone to erros, and a good documentation of experiments is vital
for scientific work, we created WRFtamer. WRFtamer most tasks listed above. In addtion, 
the work is organized and documented for later reference and documentation. Key Features
of WRFtamer include:

- Organize projects and experiments with a defined directory tree.
- Link files as required.
- Run WPS on demand.
- Automatically document your work to be able to reproduce a run with minimal effort.
- Postprocess output.
- Archive completed runs.
- Get an overview of used computing ressources of a project (runtime, disk usage etc).

