# coding: utf-8
import os

"""
This script will initialize the namelist.input (WRF) and namelist.wps (WPS).
It is needed to provide a config-file which contains information about the desired setting,
and a namelist.template
"""


def initialize_wrf_namelist(namelist_vars: dict, namelistfile: str, templatefile=None):
    # read template and configuration
    if templatefile is None:
        mypath = (
            os.path.split(os.path.realpath(__file__))[0]
            + "/../wrftamer/resources/namelist.template"
        )
    else:
        mypath = templatefile

    max_keylen = 0
    dom_keys = (
        "start_year start_month start_day start_hour start_date "
        "end_year end_month end_day end_hour end_date"
    )

    with open(mypath, "r") as f:

        tpl = f.read()
        namelist = tpl.format(**namelist_vars).split("\n")

        section = None
        # loop over all lines in the namelist template and reconstruct each one
        # using proper formatting and the corresponding values from the config file
        for line_nb, line in enumerate(namelist):
            if "&" in line:
                section = line.strip()[1:]
            elif line.strip() == "/":
                section = None
            if "=" not in line:
                continue
            key_full, val = line.split("=")
            key = key_full.strip()
            if key in dom_keys:
                val = " ".join([val.strip()] * namelist_vars["max_dom"])
            elif key in namelist_vars:
                val = str(namelist_vars[key]) + ","

            if section == "geogrid" and key in "dx dy":
                val = str(str(namelist_vars[key]).split(",")[0] + ",")

            if key == "run_hours":
                val = (
                    namelist_vars["dtend"] - namelist_vars["dtbeg"]
                ).total_seconds() // 3600
                val = f"{val:02.0f},"
            if section == "domains" and key == "eta_levels":
                # we might need to insert custom eta levels at this point
                eta_keys = [
                    k for k in namelist_vars.keys() if k.startswith("eta_levels")
                ]
                if eta_keys:
                    key = eta_keys[0]
                    val = namelist_vars[eta_keys[0]]
                    # append the remaining lines to the "value" (a bit hacky)
                    for eta_key in eta_keys[1:]:
                        val += "\n" + " ".join(
                            [
                                eta_key,
                                " " * (100 - len(eta_key)),
                                "=",
                                namelist_vars[eta_key],
                            ]
                        )
                        max_keylen = max(len(eta_key), max_keylen)
            elem = str(val).split(",")
            if (len(elem) > namelist_vars["max_dom"]) and not key.startswith(
                "eta_levels"
            ):
                val = ",".join(elem[: namelist_vars["max_dom"]]) + ","

            # update this line of the namelist
            namelist[line_nb] = " ".join([key, " " * (100 - len(key)), "=", val])
            max_keylen = max(len(key), max_keylen)

    with open(namelistfile, "w") as f:
        f.write("\n".join(namelist).replace(" " * (100 - max_keylen), ""))
