import panel as pn
import panel.widgets as pnw
import datetime as dt
import pandas as pd
from pathlib import Path
from wrftamer.gui.gui_base import gui_base
from wrftamer.project_management import project, list_projects, list_unassociated_exp
from wrftamer.experiment_management import experiment
from wrftamer.wrfplotter_utility import get_available_obs, get_available_doms, get_vars_per_plottype, \
    get_lev_per_plottype_and_var, error_message, error_message2, get_newfilename_from_old

from wrftamer.wrfplotter_classes import Map
from wrftamer.plotting.collect_infos import set_infos
from wrftamer.plotting.load_and_prepare import load_obs_data, load_mod_data
from wrftamer.plotting.hv_plots import create_hv_plot
from wrftamer.plotting.mpl_plots import create_mpl_plot


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
    Manual tests of gui NOT sucessful (WRFTamer Version 1.1)
    FIXME: zt-Plot (fixed = mpl) leads to error
    FIXME: Load Data does not work properly. (Data is loaded, but routine not finished.
    FIXME: max of mpl plots fixed to 30 m/s -> dynamic!
    Rest seems to work.
    """

    def __init__(self):
        super(wrfplotter_tab, self).__init__()

        # Available observations in os['OBSERVATIONS_PATH']
        self.dataset_dict, self.list_of_obs = get_available_obs()
        self.plottypes_avil = ['Timeseries', 'Profiles', 'Obs vs Mod', 'zt-Plot', 'Map']
        self.dict_of_vars_per_plottype = get_vars_per_plottype()  # prefefined. Not dynamically
        self.dict_of_levs_per_plottype_and_var = get_lev_per_plottype_and_var()  # prefefined. Not dynamically

        # add to self?
        list_of_projects = list_projects(verbose=False)
        list_of_experiments = list_unassociated_exp(verbose=False)
        list_of_ave_windows = ['raw', '5 min Ave', '10 min Ave', '30 min Ave']

        # Menu 1
        self.mc_proj = pn.widgets.MultiChoice(name='Choose Project', max_items=1, value=[], options=list_of_projects,
                                              height=75)
        self.mc_exp = pn.widgets.MultiChoice(name='Choose Experiment', value=[''], options=list_of_experiments,
                                             height=200)

        self.sel_dom = pn.widgets.Select(name='Domain', options=[])
        self.sel_loc = pn.widgets.Select(name='Model data at', options=[])
        self.sel_obs = pn.widgets.Select(name='Observation at', options=self.list_of_obs)
        self.but_dev = pn.widgets.Button(name='Sonic', button_type='default')
        self.sel_ave = pn.widgets.Select(name='Averaging', options=list_of_ave_windows)

        # this is just a random default. Must pick reasonable values for each proj_name!
        time_values = (dt.datetime(2020, 5, 1, 0, 0), dt.datetime(2020, 5, 6, 0, 0))
        # is updated at exp_selection.
        # question: what happens if I have multiple exps with different time limits?
        self.time_to_plot = pn.widgets.DatetimeInput(name='Datetime Input', value=time_values[0])
        self.chk_static = pn.widgets.Checkbox(name='Static Plots')

        self.but_load = pn.widgets.Button(name='Load Data', button_type='default')
        self.progress = pn.indicators.Progress(name='Progress', value=0, width=300, visible=False)
        self.progress.visible = False

        # Menu2
        self.sel_var = pn.widgets.Select(name='Variable', options=self.dict_of_vars_per_plottype['Timeseries'])
        self.sel_lev = pn.widgets.Select(name='Level', options=self.dict_of_levs_per_plottype_and_var['Timeseries'][
            'WSP_Sonic'])

        self.sel_store = pn.widgets.Select(name='data type', options=['markdown', 'csv'])
        self.but_store_tab = pn.widgets.Button(name='Save Table', button_type='default', width=140, margin=[23, 10])
        self.but_store_fig = pn.widgets.Button(name='Save Figure', button_type='default', width=140, margin=[23, 10])
        self.but_store_fig.disabled = True

        self.alert1 = pn.pane.Alert('Time series data should be reloaded', alert_type="danger")
        self.alert1.visible = False

        self.alert2 = pn.pane.Alert('Map data may have to be reloaded', alert_type="warning")
        self.alert2.visible = False

        # Map Menu
        self.but_left = pn.widgets.Button(name='\u25c0', width=50)
        self.but_right = pn.widgets.Button(name='\u25b6', width=50)
        self.png_pane = pn.pane.PNG(None, width=500)

        # wrfplotter variables
        self.stats = None
        self.figure = None
        self.obs_data = dict()
        self.mod_data = dict()
        self.map_cls = None

        self.plot_panel = create_plot_panel(self.plottypes_avil)

        self._updates()

        # ---------------------------------------------------------------------------------------------------
        # --------------------------------------- Button interactions ---------------------------------------
        # ---------------------------------------------------------------------------------------------------

        # noinspection PyUnusedLocal
        def _toggle_dev(event):

            if self.but_dev.name == 'Sonic':
                self.but_dev.name = 'Analog'
            else:
                self.but_dev.name = 'Sonic'

        # noinspection PyUnusedLocal
        def _load_data(event):

            try:
                proj_name = self.mc_proj.value[0]
            except IndexError:
                proj_name = None

            plottype = self.plottypes_avil[self.plot_panel.active]
            dom = self.sel_dom.value

            if plottype in ['Timeseries', 'Profiles', 'Obs vs Mod', 'zt-Plot']:

                ave = self.sel_ave.value
                dev = self.but_dev.name
                ttp = self.time_to_plot.value

                infos = set_infos(proj_name=proj_name, domain=dom, ave=ave, device=dev, time_to_plot=ttp)

                self.progress.visible = True

                # --------------------------------------
                #                Obs
                # --------------------------------------
                self.obs_data = dict()  # to make sure that no nonesens is kept in memory
                self.progress.bar_color = 'info'
                for idx, obs in enumerate(self.list_of_obs):
                    dataset = self.dataset_dict[obs]
                    load_obs_data(self.obs_data, obs, dataset, **infos)
                    progress_value = int(100 * (idx + 1) / len(self.list_of_obs))
                    self.progress.value = progress_value

                # --------------------------------------
                #                Mod
                # --------------------------------------
                self.mod_data = dict()  # to make sure that no nonesens is kept in memory
                self.progress.bar_color = 'primary'
                self.progress.value = 0
                try:
                    proj_name = infos['proj_name']
                except KeyError:
                    proj_name = None

                proj = project(proj_name)
                list_of_exps = proj.list_exp(verbose=False)

                for idx, exp_name in enumerate(list_of_exps):
                    load_mod_data(self.mod_data, exp_name, **infos)
                    progress_value = int(100 * (idx + 1) / len(list_of_exps))
                    self.progress.value = progress_value

                self.progress.visible = False
                self.but_load.button_type = 'success'
                self.alert1.visible = False

            elif plottype == 'Map':
                # --------------------------------------
                #                Map
                # --------------------------------------
                self.map_cls = None
                try:
                    var = self.sel_var.value
                    lev = self.sel_lev.value

                    exp_name = self.mc_exp.value[0]
                    exp = experiment(proj_name, exp_name)
                    i_path = exp.exp_path / 'out'

                    # poi_file = os.environ['WRFTAMER_POI_FILE'] # Future
                    # testing.
                    # TODO: generalize!
                    poi_file = '/home/daniel/projects/parkcast/repos/WRFtamer/wrftamer/resources/Koordinaten_Windpark.csv'
                    poi = pd.read_csv(poi_file, delimiter=';')
                    self.map_cls = Map(poi=poi, intermediate_path=i_path)
                    self.map_cls.load_intermediate(dom, var, lev, '*')

                    self.alert2.visible = False
                except Exception as e:
                    print(e)
            else:
                pass

        # noinspection PyUnusedLocal
        def _store_table(event):

            self.but_store_tab.button_type = 'warning'
            extension = self.sel_store.value
            try:
                if extension == 'csv':
                    self.stats.to_csv(self.plot_path + 'Statistics.csv')
                    print('Data Stored to file Statistics.csv')
                elif extension == 'markdown':
                    self.stats.to_markdown(self.plot_path + 'Statistics.md')
                    print('Data Stored to file Statistics.md')
            except Exception as e:
                print(e)
                print(type(self.stats))

            self.but_store_tab.button_type = 'success'

        # noinspection PyUnusedLocal
        def _store_figure(event):
            self.but_store_fig.button_type = 'warning'

            # TODO: in the future, use plot_path an generate a meaningful name.
            #  self.plot_path

            self.figure.savefig('test.png', dpi=400)

            self.but_store_fig.button_type = 'success'

        # noinspection PyUnusedLocal
        def _change_pic_left(event):
            current_filename = Path(self.png_pane.object)  # The filename must be Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png
            new_filename = get_newfilename_from_old(current_filename, -10)  # For now, delta_t is fixed to 10 minuts
            self.png_pane.object = str(new_filename)

        # noinspection PyUnusedLocal
        def _change_pic_right(event):
            current_filename = Path(self.png_pane.object)  # The filename must be Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png
            new_filename = get_newfilename_from_old(current_filename, +10)  # For now, delta_t is fixed to 10 minuts
            self.png_pane.object = str(new_filename)

        # Button click events
        self.but_dev.on_click(_toggle_dev)
        self.but_load.on_click(_load_data)
        self.but_store_tab.on_click(_store_table)
        self.but_store_fig.on_click(_store_figure)
        self.but_left.on_click(_change_pic_left)
        self.but_right.on_click(_change_pic_right)

    def _updates(self):

        @pn.depends(self.mc_proj.param.value, self.mc_exp.param.value, watch=True)
        def _update_sel_loc(proj_list, exp_list):

            try:
                proj_name = proj_list[0]
                exp_name = exp_list[0]

                exp = experiment(proj_name, exp_name)
                list_of_locs = exp.list_tslocs(False)
            except:
                list_of_locs = []

            self.sel_loc.options = list_of_locs

        @pn.depends(self.mc_proj.param.value, watch=True)
        def _update_sel_dom(proj_list):

            try:
                proj_name = proj_list[0]
            except KeyError:
                proj_name = None

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

            try:
                proj_name = self.mc_proj.value[0]
            except IndexError:
                proj_name = None

            try:
                exp_name = selection[0]
                # for now, always use the first one. In the future, select all and find min,max.

                exp = experiment(proj_name, exp_name)
                time_values = exp.start_end(False)
                self.time_to_plot.value = time_values[0]
            except IndexError:
                pass

        # noinspection PyUnusedLocal
        @pn.depends(self.mc_proj.param.value, self.sel_dom.param.value,
                    self.but_dev.param.name, self.sel_ave.param.value, watch=True)
        def _reload_watcher1(proj, dom, dev, ave):
            # Watches for changes in relevant parameters and indicates that a reload is needed
            self.alert1.visible = True

        # noinspection PyUnusedLocal
        @pn.depends(self.mc_proj.param.value, self.mc_exp.param.value, self.sel_dom.param.value,
                    self.sel_var.param.value, self.sel_lev.param.value, watch=True)
        def _reload_watcher2(proj, exp_names, dom, var, lev):
            # Watches for changes in relevant parameters and indicates that a reload is needed
            # This is for maps
            self.alert2.visible = True

        # udating widgets related to table and figure storing
        @pn.depends(self.plot_panel.param.active, self.chk_static.param.value, watch=True)
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

        @pn.depends(self.plot_panel.param.active, self.sel_var.param.value, self.but_dev.param.name, watch=True)
        def _update_sel_lev(active, var, device):

            if var in ['WSP', 'DIR', 'WSP and DIR', 'WSP and PT'] and active in [0, 2]:
                tmp_var = var + '_' + device
            else:
                tmp_var = var

            plottype = self.plottypes_avil[active]

            if active in [1]:
                self.sel_lev.disabled = True
                self.sel_lev.options = []
            else:
                self.sel_lev.disabled = False
                self.sel_lev.options = self.dict_of_levs_per_plottype_and_var[plottype][tmp_var]

        @pn.depends(self.plot_panel.param.active,
                    self.mc_proj.param.value, self.mc_exp.param.value, self.sel_dom.param.value,
                    self.sel_loc.param.value,
                    self.sel_obs.param.value, self.but_dev.param.name, self.sel_ave.param.value,
                    self.sel_var.param.value, self.sel_lev.param.value, self.time_to_plot.param.value,
                    self.chk_static.param.value, watch=True)
        def _create_plot(active, proj_list, exp_list, dom, loc, obs, dev, ave, var, lev, ttp, static_plots):

            plottype = self.plottypes_avil[active]

            try:
                proj_name = proj_list[0]

                if plottype in ['Timeseries', 'Profiles', 'Obs vs Mod', 'zt-Plot']:

                    infos = set_infos(proj_name=proj_name, domain=dom, variable=var, level=lev, run=exp_list,
                                      ftype='tslist',
                                      plottype=plottype, time_to_plot=ttp, ave=ave, device=dev, location=loc,
                                      observation=obs)

                    if static_plots:
                        figure = create_mpl_plot(obs_data=self.obs_data, mod_data=self.mod_data, infos=infos)
                        self.stats = None
                        self.figure = figure
                    else:
                        figure, self.stats = create_hv_plot(infos, obs_data=self.obs_data, mod_data=self.mod_data)

                elif plottype == 'Map':

                    if static_plots:

                        exp = experiment(proj_name, exp_list[0])
                        timestamp = ttp.strftime('%Y%m%d_%H%M%S')
                        filename = exp.exp_path / f'plot/Map_{dom}_{var}_{timestamp}_ml{lev}.png'

                        if filename.is_file():
                            self.png_pane.object = str(filename)
                            figure = pn.Column(self.png_pane, pn.Row(self.but_left, self.but_right))
                        else:
                            figure = error_message2(filename)
                    else:
                        try:
                            # TODO: This is not very nice, but the best I can do right now.
                            #  Also, the size is too large, but I cannot change this right now, an I do not
                            #  have time to play around with this issue.
                            # One thing I found out: if you drop XTIME from the xarray, at least the title is
                            # better.
                            figure = self.map_cls.data.interactive.sel(Time=pnw.DiscreteSlider).plot()
                        except Exception as e:
                            figure = error_message(e)

                else:
                    figure = None

                tab = (plottype, figure)
            except Exception as e:
                message = error_message(e)
                tab = (plottype, message)

            self.plot_panel[active] = tab

    def view(self):

        menu1 = pn.Column(self.mc_proj, self.mc_exp, self.sel_dom, self.sel_loc, self.sel_obs,
                          self.but_dev, self.sel_ave, self.time_to_plot, self.chk_static,
                          self.progress, self.but_load)
        menu2 = pn.Row(
            pn.Column(pn.Row(self.sel_var, self.sel_lev),
                      pn.Row(self.sel_store, self.but_store_tab, self.but_store_fig)),
            pn.Column(self.alert1, self.alert2)
        )

        wp = pn.Row(menu1, pn.Column(menu2, self.plot_panel), name='WRFplotter')

        return wp
