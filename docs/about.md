# About

## Release Notes

**Version 1.1.0 - 22.03.2022**
Added functionallity
- A watchdog to automatically perform postprocessing once a run is finished.
- the actions performed automatically are defined in the "postprocessing protocol", a section in the configure.yaml file.
- The column "archived" of the xlsx files is renamed to "status". It contains now a string describing the status
of an experiment instead of a boolean.
- The status of each experiment is now listed in the GUIs project tab.
- WRFplotter, a GUI to create interactive standard plots like timeseries, profiles, maps and zt plots has been added to the GUI.
- WRFplotter may display observation of your choosing, provided they are in a format WRFplotter can read. See [WRFplotter](wrfplotter.md) for more information.

Minor changes:
- bugfixes
- timeseries produced by the tslist processing are now in a (mostly) cf-conform datastructure.
- General imporovements to the code.


**Version 1.0.0 - 16.02.2022**

- WRFtamer is publicly available now.

**Future Releases**

- Add a watchdog to automatically perform postprocessing once a run is finished.

<!--
- Should the EXP_NAME.yaml file be deleted once wt create has been executed? Afte all, the 
  configure.yaml file is here anyway, and I don't want to cause confusion. Furthermore, the .yaml files
  may pile up.
- remove link_grib from list of essential files? We have replaced the file with a python version, that is more dynamic. (works for GRIBFILE_XXXX.
-->

## Contributing

Please refer to these [guidelines](https://github.com/os-simopt/WRFtamer/blob/main/CONTRIBUTING.md).

## Licence

WRFtamer is licenced under the MIT Licence. You find the full legal text in the file 
[LICENCE](https://github.com/os-simopt/WRFtamer/blob/main/LICENCE).

## Acknowledgements

This work has been supported by
- German Federal Ministry for Economic Affairs and Energy (BMWI)
- Zentrum für Sonnenenergie- und Wasserstoff-Forschung Baden-Württemberg (ZSW)
