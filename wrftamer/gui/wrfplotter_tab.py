import panel as pn
import panel.widgets as pnw
import datetime as dt
import pandas as pd
from pathlib import Path
from wrftamer.gui.gui_base import gui_base
from wrftamer.main import project, list_projects, list_unassociated_exp

from wrftamer.gui.wrfplotter_utility import (
    get_available_obs,
    get_available_doms,
    get_vars_per_plottype,
    get_lev_per_plottype_and_var,
    error_message,
    error_message2,
    get_newfilename_from_old,
)

from wrftamer.wrfplotter_classes import Map
from wrftamer.plotting.load_and_prepare import load_obs_data, load_mod_data
from wrftamer.plotting.load_and_prepare import (
    prep_profile_data,
    prep_ts_data,
    prep_zt_data,
    get_limits_and_labels,
)
from wrftamer.plotting.hv_plots import create_hv_plot
from wrftamer.plotting.mpl_plots import create_mpl_plot
from wrftamer.utility import get_random_string
import holoviews as hv

hv.extension("bokeh")


def create_plot_panel(plottypes_avil):
    # Creates an empty plot panel
    tabs = []
    for plottype in plottypes_avil:
        tmp = (plottype, None)
        tabs.append(tmp)

    tabs = tuple(tabs)
    panel = pn.Tabs(*tabs)

    return panel


class wrfplotter_tab(gui_base):
    """
    Manual tests of gui sucessful (WRFTamer Version 1.1)
    """

    def __init__(self):
        super(wrfplotter_tab, self).__init__()

        # Available observations in os['OBSERVATIONS_PATH']
        self.dataset_dict, self.list_of_obs = get_available_obs()
        self.plottypes_avil = [
            "Timeseries",
            "Profiles",
            "Obs vs Mod",
            "Histogram",
            "Windrose",
            "zt-Plot",
            "Map",
            "MapSequence",
        ]
        self.dict_of_vars_per_plottype = (
            get_vars_per_plottype()
        )  # prefefined. Not dynamically
        self.dict_of_levs_per_plottype_and_var = (
            get_lev_per_plottype_and_var()
        )  # prefefined. Not dynamically

        # add to self?
        list_of_projects = list_projects(verbose=False)
        list_of_experiments = list_unassociated_exp(verbose=False)
        list_of_ave_windows = ["raw", "5 min Ave", "10 min Ave", "30 min Ave"]

        # Menu 1
        self.mc_proj = pn.widgets.MultiChoice(
            name="Choose Project",
            max_items=1,
            value=[],
            options=list_of_projects,
            height=75,
        )
        self.mc_exp = pn.widgets.MultiChoice(
            name="Choose Experiment",
            value=[""],
            options=list_of_experiments,
            height=200,
        )

        self.sel_dom = pn.widgets.Select(name="Domain", options=[])
        self.sel_loc = pn.widgets.Select(name="Model data at", options=[])
        self.sel_obs = pn.widgets.Select(
            name="Observation at", options=self.list_of_obs
        )
        self.but_dev = pn.widgets.Button(name="Sonic", button_type="default")
        self.sel_ave = pn.widgets.Select(name="Averaging", options=list_of_ave_windows)

        # this is just a random default. Must pick reasonable values for each proj_name!
        time_values = (dt.datetime(2020, 5, 1, 0, 0), dt.datetime(2020, 5, 6, 0, 0))
        # is updated at exp_selection.
        # question: what happens if I have multiple exps with different time limits?
        self.time_to_plot = pn.widgets.DatetimeInput(
            name="Datetime Input", value=time_values[0]
        )
        self.chk_static = pn.widgets.Checkbox(name="Static Plots")

        self.but_load = pn.widgets.Button(name="Load Data", button_type="default")
        self.progress = pn.indicators.Progress(
            name="Progress", value=0, width=300, visible=False
        )
        self.progress.visible = False

        # Menu2
        self.sel_var = pn.widgets.Select(
            name="Variable", options=self.dict_of_vars_per_plottype["Timeseries"]
        )
        self.sel_lev = pn.widgets.Select(
            name="height",
            options=self.dict_of_levs_per_plottype_and_var["Timeseries"]["WSP_Sonic"],
        )

        self.sel_store = pn.widgets.Select(
            name="data type", options=["markdown", "csv"]
        )
        self.but_store_tab = pn.widgets.Button(
            name="Save Table", button_type="default", width=140, margin=[23, 10]
        )
        self.but_store_fig = pn.widgets.Button(
            name="Save Figure", button_type="default", width=140, margin=[23, 10]
        )
        self.but_store_fig.disabled = True

        self.alert1 = pn.pane.Alert(
            "Time series data should be reloaded", alert_type="danger"
        )
        self.alert1.visible = False

        self.alert2 = pn.pane.Alert(
            "Map data may have to be reloaded", alert_type="warning"
        )
        self.alert2.visible = False

        # Map Menu
        self.but_left = pn.widgets.Button(name="\u25c0", width=50)
        self.but_right = pn.widgets.Button(name="\u25b6", width=50)
        self.png_pane = pn.pane.PNG(None, width=500)

        # Manual Settings
        title = pn.widgets.TextInput(placeholder="title")
        xlabel = pn.widgets.TextInput(placeholder="xlabel")
        ylabel = pn.widgets.TextInput(placeholder="ylabel")
        font_size = pn.widgets.IntSlider(
            name="Font Size", value=15, start=10, end=25, step=1
        )
        xlim_a = pn.widgets.RangeSlider(
            name="xlim", start=0, end=50, value=(0, 50), step=0.01
        )
        xlim_b = pn.widgets.DateRangeSlider(
            name="xlim (time)",
            start=dt.datetime(2020, 1, 1),
            end=dt.datetime(2021, 1, 1),
            value=(dt.datetime(2020, 1, 1), dt.datetime(2021, 1, 10)),
        )
        xlim_b.visible = False
        ylim = pn.widgets.RangeSlider(
            name="ylim", start=0, end=50, value=(0, 50), step=0.01
        )
        clim = pn.widgets.RangeSlider(
            name="clim", start=0, end=100, value=(0, 50), step=0.01
        )
        clim.visible = False
        default_poi = "lat; lon\n 50.45; 9.8 \n 45.1,7.5 \n"
        poi_data = pn.widgets.input.TextAreaInput(
            name="points of interest", placeholder=default_poi, height=100
        )
        self.but_render = pn.widgets.Button(name="Render Plot", button_type="success")
        self.card_ms = pn.Card(
            title,
            xlabel,
            ylabel,
            font_size,
            xlim_a,
            xlim_b,
            ylim,
            clim,
            poi_data,
            self.but_render,
            title="Manual Settings",
        )
        self.card_ms.collapsed = True
        # TODO: write update function for the card_ms
        # TODO: modify reder_plot need manual values sent to plot routine.

        # wrfplotter variables
        self.stats = None
        self.figure = None
        self.obs_data = dict()
        self.mod_data = dict()
        self.data = None
        self.map_cls = None
        self.infos = dict()

        self.plot_panel = create_plot_panel(self.plottypes_avil)

        self._updates()

        # ---------------------------------------------------------------------------------------------------
        # --------------------------------------- Button interactions ---------------------------------------
        # ---------------------------------------------------------------------------------------------------

        # noinspection PyUnusedLocal
        def _toggle_dev(event):

            if self.but_dev.name == "Sonic":
                self.but_dev.name = "Analog"
            else:
                self.but_dev.name = "Sonic"

        # noinspection PyUnusedLocal
        def _load_data(event):

            plottype = self.plottypes_avil[self.plot_panel.active]

            proj_name = self.gui_status["proj_name"]
            dom = self.gui_status["dom"]
            var = self.gui_status["var"]
            lev = self.gui_status["lev"]

            if plottype in ["Timeseries", "Profiles", "Obs vs Mod", "zt-Plot"]:

                self.progress.visible = True

                # --------------------------------------
                #                Obs
                # --------------------------------------
                self.obs_data = (
                    dict()
                )  # to make sure that no nonesens is kept in memory
                self.progress.bar_color = "info"

                for idx, obs in enumerate(self.list_of_obs):
                    dataset = self.dataset_dict[obs]
                    load_obs_data(self.obs_data, obs, dataset, **self.gui_status)
                    progress_value = int(100 * (idx + 1) / len(self.list_of_obs))
                    self.progress.value = progress_value

                # --------------------------------------
                #                Mod
                # --------------------------------------
                self.mod_data = (
                    dict()
                )  # to make sure that no nonesens is kept in memory
                self.progress.bar_color = "primary"
                self.progress.value = 0

                if proj_name is None:
                    self.mod_data = None
                else:
                    proj = project(proj_name)
                    list_of_exps = proj.list_exp(verbose=False)

                    for idx, exp_name in enumerate(list_of_exps):
                        load_mod_data(self.mod_data, exp_name, **self.gui_status)
                        progress_value = int(100 * (idx + 1) / len(list_of_exps))
                        self.progress.value = progress_value

                self.progress.visible = False
                self.but_load.button_type = "success"
                self.alert1.visible = False

            elif plottype in ["Map", "MapSequence"]:
                # --------------------------------------
                #                Map,MapSequence
                # --------------------------------------

                self.map_cls = None
                try:

                    proj = project(proj_name)
                    exp_name = self.mc_exp.value[0]

                    i_path = proj.get_workdir(exp_name) / "out"

                    self.map_cls = Map(intermediate_path=i_path)
                    self.map_cls.load_intermediate(dom, var, lev, "*")

                    # TODO: Temporary fix for units. -> rerun intermediate files.
                    self.map_cls.data.attrs["units"] = "m s-1"

                    self.alert2.visible = False
                except Exception as e:
                    print(e)
            else:
                pass

            # Call the plot routine to create a new plot directly after data is loaded.
            self.prepare_data()
            self.create_plot(self.plot_panel.active, self.chk_static.value)  #

        # noinspection PyUnusedLocal
        def _store_table(event):

            self.but_store_tab.button_type = "warning"
            extension = self.sel_store.value
            try:
                if extension == "csv":
                    self.stats.to_csv(self.plot_path + "Statistics.csv")
                    print("Data Stored to file Statistics.csv")
                elif extension == "markdown":
                    self.stats.to_markdown(self.plot_path + "Statistics.md")
                    print("Data Stored to file Statistics.md")
            except Exception as e:
                print(e)

            self.but_store_tab.button_type = "success"

        # noinspection PyUnusedLocal
        def _store_figure(event):
            self.but_store_fig.button_type = "warning"

            filename = "WP_" + get_random_string(30) + ".png"
            file2save = self.plot_path / filename

            self.figure.savefig(file2save, dpi=400)

            self.but_store_fig.button_type = "success"

        # noinspection PyUnusedLocal
        def _change_pic_left(event):
            current_filename = Path(self.png_pane.object)
            # The filename must be Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png
            new_filename = get_newfilename_from_old(current_filename, -10)
            # For now, delta_t is fixed to 10 minuts
            self.png_pane.object = str(new_filename)

        # noinspection PyUnusedLocal
        def _change_pic_right(event):
            current_filename = Path(self.png_pane.object)
            # The filename must be Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png
            new_filename = get_newfilename_from_old(current_filename, +10)
            # For now, delta_t is fixed to 10 minuts
            self.png_pane.object = str(new_filename)

        # noinspection PyUnusedLocal
        def _render_plot(event):

            if self.gui_status["get_limits"] == "manual":
                # Update Infos from Manual Settings
                self.infos.update(
                    {
                        "title": self.card_ms[0].value,
                        "xlabel": self.card_ms[1].value,
                        "ylabel": self.card_ms[2].value,
                        "font_size": self.card_ms[3].value,
                        "xlim": self.card_ms[4].value,
                        "tlim": (
                            pd.Timestamp(self.card_ms[5].value[0]),
                            pd.Timestamp(self.card_ms[5].value[1]),
                        ),
                        "ylim": self.card_ms[6].value,
                        "clim": self.card_ms[7].value,
                        "poi": None,
                    }
                )

                # I guess I need to read the poi file? Set to None for now.
                # self.card_ms[7].value

            self.create_plot(self.plot_panel.active, self.chk_static.value)

        # Button click events
        self.but_dev.on_click(_toggle_dev)
        self.but_load.on_click(_load_data)
        self.but_store_tab.on_click(_store_table)
        self.but_store_fig.on_click(_store_figure)
        self.but_left.on_click(_change_pic_left)
        self.but_right.on_click(_change_pic_right)
        self.but_render.on_click(_render_plot)

    # ---------------------------------------------------------------------------------------------------
    @property
    def gui_status(self):
        """

        Returns: A dict that stores the status of the gui. Is updated every time the gui_status is called.

        """

        infos = dict()

        try:
            infos["proj_name"] = self.mc_proj.value[0]
        except IndexError:
            infos["proj_name"] = None

        try:
            infos["Expvec"] = self.mc_exp.value
        except IndexError:
            infos["Expvec"] = None

        infos["dom"] = self.sel_dom.value
        infos["loc"] = self.sel_loc.value
        infos["Obsvec"] = [self.sel_obs.value]  # may be a multiselector in the future.
        infos["anemometer"] = self.but_dev.name

        translate = {"raw": 0, "5 min Ave": 5, "10 min Ave": 10, "30 min Ave": 30}
        infos["AveChoice_WRF"] = translate[self.sel_ave.value]
        infos["AveChoice_OBS"] = translate[self.sel_ave.value]
        infos["dom"] = self.sel_dom.value
        infos["var"] = self.sel_var.value
        infos["lev"] = self.sel_lev.value

        infos["time_to_plot"] = self.time_to_plot.value

        infos["static"] = self.chk_static.value
        infos["store_datatype"] = self.sel_store.value

        infos["active"] = self.plot_panel.active
        infos["plottype"] = self.plottypes_avil[self.plot_panel.active]

        if self.card_ms.collapsed:
            infos["get_limits"] = "auto"
        else:
            infos["get_limits"] = "manual"

        infos["ms_menu_collapsed"] = self.card_ms.collapsed

        return infos

    # ---------------------------------------------------------------------------------------------------
    # --------------------------------------- Update Functions ------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    def _updates(self):

        """
        @pn.depends(self.chk_static.param.value, watch=True)
        def _update_extension(static):
            if static:
                hv.extension('matplotlib')
            else:
                hv.extension('bokeh')
        """

        @pn.depends(self.mc_proj.param.value, self.mc_exp.param.value, watch=True)
        def _update_sel_loc(proj_list, exp_list):

            try:
                proj_name = proj_list[0]
                exp_name = exp_list[0]

                proj = project(proj_name)
                list_of_locs = proj.exp_list_tslocs(exp_name, False)
            except:
                list_of_locs = []

            self.sel_loc.options = list_of_locs

        @pn.depends(self.mc_proj.param.value, watch=True)
        def _update_sel_dom(proj_list):

            proj_name = self.gui_status["proj_name"]
            list_of_doms = get_available_doms(proj_name)
            self.sel_dom.options = list_of_doms

        @pn.depends(self.mc_proj.param.value, watch=True)
        def _update_exp_list(selection):
            if len(selection) == 1:
                proj_name = selection[0]
                proj = project(proj_name)

                new_options = proj.list_exp(verbose=False)
                self.mc_exp.options = new_options

            else:
                self.mc_exp.options = list_unassociated_exp(verbose=False)

        @pn.depends(self.mc_exp.param.value, watch=True)
        def _update_ttp(selection):  # time to plot

            proj_name = self.gui_status["proj_name"]

            try:
                exp_name = selection[0]
                # for now, always use the first one. In the future, select all and find min,max.

                proj = project(proj_name)
                time_values = proj.exp_start_end(exp_name, False)

                self.time_to_plot.value = time_values[0]
            except IndexError:
                pass

        # noinspection PyUnusedLocal
        @pn.depends(
            self.mc_proj.param.value,
            self.sel_dom.param.value,
            self.but_dev.param.name,
            self.sel_ave.param.value,
            watch=True,
        )
        def _reload_watcher1(proj, dom, dev, ave):
            # Watches for changes in relevant parameters and indicates that a reload is needed
            self.alert1.visible = True

        # noinspection PyUnusedLocal
        @pn.depends(
            self.mc_proj.param.value,
            self.mc_exp.param.value,
            self.sel_dom.param.value,
            self.sel_var.param.value,
            self.sel_lev.param.value,
            watch=True,
        )
        def _reload_watcher2(proj, exp_names, dom, var, lev):
            # Watches for changes in relevant parameters and indicates that a reload is needed
            # This is for maps
            self.alert2.visible = True

        # udating widgets related to table and figure storing
        @pn.depends(
            self.plot_panel.param.active, self.chk_static.param.value, watch=True
        )
        def _update_store(active, static_plots):
            if active in [0, 2]:
                self.sel_store.disabled = False
                self.but_store_tab.disabled = False
            else:
                self.sel_store.disabled = True
                self.but_store_tab.disabled = True

            if static_plots:
                self.but_store_fig.disabled = False
            else:
                self.but_store_fig.disabled = True

        @pn.depends(self.plot_panel.param.active, watch=True)
        def _update_sel_var(active):
            plottype = self.plottypes_avil[active]
            self.sel_var.options = self.dict_of_vars_per_plottype[plottype]

        @pn.depends(
            self.plot_panel.param.active,
            self.sel_var.param.value,
            self.but_dev.param.name,
            watch=True,
        )
        def _update_sel_lev(active, var, device):

            if var in ["WSP", "DIR", "WSP and DIR", "WSP and PT"] and active in [0, 2]:
                tmp_var = var + "_" + device
            else:
                tmp_var = var

            plottype = self.plottypes_avil[active]

            if active in [1, 3]:
                self.sel_lev.disabled = True
                self.sel_lev.options = []
            else:
                self.sel_lev.disabled = False
                self.sel_lev.options = self.dict_of_levs_per_plottype_and_var[plottype][
                    tmp_var
                ]

            if plottype in ["Map"]:
                self.sel_lev.name = "level"
            else:
                self.sel_lev.name = "height"

        @pn.depends(
            self.plot_panel.param.active,
            self.mc_proj.param.value,
            self.mc_exp.param.value,
            self.sel_dom.param.value,
            self.sel_loc.param.value,
            self.sel_obs.param.value,
            self.but_dev.param.name,
            self.sel_ave.param.value,
            self.sel_var.param.value,
            self.sel_lev.param.value,
            self.time_to_plot.param.value,
            self.chk_static.param.value,
            watch=True,
        )  # I guess this watcher makes my gui somewhat slow?
        def _update_plot(
                active,
                proj_list,
                exp_list,
                dom,
                loc,
                obs,
                dev,
                ave,
                var,
                lev,
                ttp,
                static_plots,
        ):  #
            self.prepare_data()  #
            self.create_plot(active, static_plots)  #

    def prepare_data(self):

        try:
            plottype = self.gui_status["plottype"]
            var = self.gui_status["var"]

            if plottype == "Profiles":
                self.data, units, description = prep_profile_data(
                    self.obs_data, self.mod_data, self.gui_status
                )
                self.infos = get_limits_and_labels(
                    plottype, var, self.data, units=units, description=description
                )

            elif plottype == "Obs vs Mod":
                self.data, units, description = prep_ts_data(
                    self.obs_data, self.mod_data, self.gui_status
                )
                self.infos = get_limits_and_labels(
                    plottype, var, self.data, units=units, description=description
                )

            elif plottype == "Timeseries":
                self.data, units, description = prep_ts_data(
                    self.obs_data, self.mod_data, self.gui_status
                )
                self.infos = get_limits_and_labels(
                    plottype, var, self.data, units=units, description=description
                )

            elif plottype == "zt-Plot":
                self.data = prep_zt_data(self.mod_data, self.gui_status)
                self.infos = get_limits_and_labels(plottype, var, self.data)

            self.infos["Expvec"] = self.gui_status["Expvec"]
            self.infos["Obsvec"] = self.gui_status["Obsvec"]
            self.infos["proj_name"] = self.gui_status["proj_name"]

            # Set Values to manual settings menu
            self.card_ms[0].value = self.infos["title"]
            self.card_ms[1].value = self.infos["xlabel"]
            self.card_ms[2].value = self.infos["ylabel"]
            self.card_ms[3].value = self.infos["font_size"]
            if "xlim" in self.infos:
                self.card_ms[4].start = self.infos["xlim"][0]
                self.card_ms[4].end = self.infos["xlim"][1]
                self.card_ms[4].visible = True
            else:
                self.card_ms[4].visible = False
            if "tlim" in self.infos:
                self.card_ms[5].start = self.infos["tlim"][0].to_pydatetime()
                self.card_ms[5].end = self.infos["tlim"][1].to_pydatetime()
                self.card_ms[5].visible = True
            else:
                self.card_ms[5].visible = False

            self.card_ms[6].start = self.infos["ylim"][0]
            self.card_ms[6].end = self.infos["ylim"][1]

            if "clim" in self.infos:
                self.card_ms[7].value = tuple(self.infos["clim"])
                self.card_ms[7].visible = True
            else:
                self.card_ms[7].visible = False

            # I can set default poi here.

        except:
            self.data = None

    def create_plot(self, active, static_plots):

        proj_name = self.gui_status["proj_name"]
        exp_list = self.gui_status["Expvec"]
        plottype = self.gui_status["plottype"]
        var = self.gui_status["var"]
        lev = self.gui_status["lev"]
        dom = self.gui_status["dom"]
        ttp = self.gui_status["time_to_plot"]

        if self.data is None and plottype not in ["Map", "MapSequence"]:
            message = error_message("No Data available")
            tab = (plottype, message)
            self.plot_panel[active] = tab
            return

        try:
            # Line Plots, based on tslists
            if static_plots and plottype in [
                "Timeseries",
                "Profiles",
                "Obs vs Mod",
                "zt-Plot",
            ]:
                self.figure = create_mpl_plot(data=self.data, infos=self.infos)
                self.stats = None
            elif not static_plots and plottype in [
                "Timeseries",
                "Profiles",
                "Obs vs Mod",
                "zt-Plot",
            ]:
                self.figure, self.stats = create_hv_plot(
                    data=self.data, infos=self.infos
                )

            # Map Sequence
            elif static_plots and plottype == "MapSequence":

                # This is not really a plot created on-the-fly, but a static view of pre-created plots.
                # Its fast though...
                # I might try creating plots based on intermediate files...
                proj = project(proj_name)
                exp_path = proj.get_workdir(exp_name=exp_list[0])

                timestamp = ttp.strftime("%Y%m%d_%H%M%S")
                filename = exp_path / f"plot/Map_{dom}_{var}_{timestamp}_ml{lev}.png"

                if filename.is_file():
                    self.png_pane.object = str(filename)
                    self.figure = pn.Column(
                        self.png_pane, pn.Row(self.but_left, self.but_right)
                    )
                else:
                    self.figure = error_message2(filename + " not found")
            elif not static_plots and plottype == "MapSequence":

                try:
                    self.figure = self.map_cls.data.interactive.sel(
                        Time=pnw.DiscreteSlider
                    ).plot()
                except Exception as e:
                    self.figure = error_message(e)

            # Map for single point in time.
            elif static_plots and plottype == "Map":
                poi = None  # FIXME
                self.figure = self.map_cls.plot("Cartopy", store=False, poi=poi, **self.gui_status)

            elif not static_plots and plottype == "Map":
                try:
                    # poi_file = poi_text.value
                    # if isinstance(poi_file, bytes):
                    #    s = str(poi_file, 'utf-8')
                    #    poi_file = StringIO(s)
                    #
                    # poi = pd.read_csv(poi_file, delimiter=';')

                    poi = None  # FIXME
                    self.figure = self.map_cls.plot("hvplot", store=False, poi=poi, **self.gui_status)
                except Exception as e:
                    self.figure = error_message(e)

            # Other plots.
            else:
                self.figure = None

            tab = (plottype, self.figure)

        except Exception as e:
            message = error_message(e)
            tab = (plottype, message)

        self.plot_panel[active] = tab

        """
        # This could be the future. Always call hvplots and just change the extension. However,
        # I get a lot of ploblems since the plots I am creating are based on hvplot and 
        # the extension switch only works with bokeh. In bokeh however, the plots must be created differently...
        # So, no update for now.
        
        if plottype in ['Timeseries', 'Profiles', 'Obs vs Mod', 'zt-Plot']:
            self.figure, self.stats = create_hv_plot(infos=self.infos, obs_data=self.obs_data, 
                                                     mod_data=self.mod_data)

        # Map Sequence
        elif plottype == 'MapSequence':

            try:
                self.figure = self.map_cls.interactive.sel(Time=pnw.DiscreteSlider).plot()
            except Exception as e:
                self.figure = error_message(e)

        # Map for single point in time.
        elif plottype == 'Map':
            try:

                # poi_file = poi_text.value
                # if isinstance(poi_file, bytes):
                #    s = str(poi_file, 'utf-8')
                #    poi_file = StringIO(s)
                #
                # poi = pd.read_csv(poi_file, delimiter=';')

                poi = None  # FIXME
                self.figure = self.map_cls.plot('hvplot', store=False, poi=poi)
            except Exception as e:
                self.figure = error_message(e)
        """

    def view(self):

        menu1 = pn.Column(
            self.mc_proj,
            self.mc_exp,
            self.sel_dom,
            self.sel_loc,
            self.sel_obs,
            self.but_dev,
            self.sel_ave,
            self.time_to_plot,
            self.chk_static,
            self.progress,
            self.but_load,
        )
        menu2 = pn.Row(
            pn.Column(
                pn.Row(self.sel_var, self.sel_lev),
                pn.Row(self.sel_store, self.but_store_tab, self.but_store_fig),
            )
        )

        side_menu = pn.Column(self.alert1, self.alert2, self.card_ms)

        wp = pn.Row(
            menu1, pn.Column(menu2, self.plot_panel), side_menu, name="WRFplotter"
        )

        return wp
