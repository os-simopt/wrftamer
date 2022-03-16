import os
import panel as pn
import re
import datetime as dt

from gui_functions import *

import wrftamer
from wrftamer.project_management import project, list_projects, list_unassociated_exp, reassociate
from wrftamer.experiment_management import experiment
from wrftamer.wrftamer_paths import wrftamer_paths
from wrftamer.wrfplotter_classes import Map
from wrftamer.plotting.collect_infos import set_infos
from wrftamer.plotting.load_and_prepare import load_obs_data, load_mod_data
from wrftamer.plotting.hv_plots import create_hv_plot


pn.extension('tabulator')
tabulator_formatters = {
    'select': {'type': 'tickCross'}
}

def wt_proj_tab(*args):
    list_of_projects = list_projects(verbose=False)
    list_of_experiments = list_unassociated_exp(verbose=False)

    global wt_mc_proj
    wt_mc_proj = pn.widgets.MultiChoice(name='Choose Project', max_items=1, value=[], options=list_of_projects,
                                     height=75)

    textbox = pn.widgets.TextInput(name='New Project Name', value='')

    b_create = pn.widgets.Button(name='Create Project', button_type='success')
    b_rename = pn.widgets.Button(name='Rename Project', button_type='warning')
    b_delete = pn.widgets.Button(name='Remove Project', button_type='danger')
    b_reassociate = pn.widgets.Button(name='Reassociate Experiments', button_type='primary')

    del_warn = pn.widgets.StaticText(name='Warning',
                                     value='This will delete all data of this project. Click again to proceed.',
                                     background='#ffcc00')
    del_warn.visible = False

    b_cancel = pn.widgets.Button(name='Cancel', button_type='warning', visible=False)

    info_panel = pn.widgets.StaticText(name='Experiments not associated with any project',
                                       value=str(len(list_of_experiments)), background='#ffffff')

    proj = project(None)
    df = proj.provide_info()
    info_df = pn.widgets.Tabulator(df, formatters=tabulator_formatters, height=600)

    def create_proj(event):

        old_options = wt_mc_proj.options.copy()
        proj_name = textbox.value

        if not re.match(r'^[A-Za-z0-9_-]+$', textbox.value):
            print('Only alphanumeric values, underscore and dash are allowed in the project name')
            return
        elif textbox.value in old_options:
            print('A project with this name already exists!')
            return
        else:
            old_options.append(textbox.value)
            wt_mc_proj.options = old_options

            ########################################
            # Do the actual project creation.
            ########################################
            proj = project(proj_name)

            try:
                proj.create()
            except FileExistsError:
                print('A project with this name already exists. Remove project or choose a different name')
                return

            if any(info_df.value.select):
                print('Combining unassociated experiments to new project')

                # Now, move the selected directories, associate with the new project and remove from unassociated
                # list. Right now, I cannot reassociate an experiment from project1 to project2. Only from
                # unassociated to associated.

                try:
                    proj_name_old = wt_mc_proj.value[0]
                except IndexError:
                    proj_name_old = None

                proj_old = project(proj_name_old)

                # first, remove from unassociated list:
                for exp_name in info_df.value.Name[info_df.value.select == True]:
                    reassociate(proj_old, proj, exp_name)  # this function changes all relevant paths, entries and
                    # moves files.

    def rename_proj(event):

        choice = wt_mc_proj.value
        new_name = textbox.value

        if len(choice) > 0 and new_name != '':
            old_options = wt_mc_proj.options.copy()

            if new_name in old_options:
                print('A project with this name already exists')
            else:
                old_options.remove(choice[0])
                old_options.append(new_name)

                wt_mc_proj.options = old_options
                wt_mc_proj.value = [new_name]

                ########################################
                # Do the actual project renaming
                ########################################
                proj = project(choice[0])

                try:
                    proj.rename(new_name)
                except FileNotFoundError:
                    print('Project does not exists. Cannot rename')
                    return
                except FileExistsError:
                    print('New Project Name already exists. Cannot rename')
                    return

    def remove_proj(event):

        choice = wt_mc_proj.value

        if len(choice) > 0:

            if not del_warn.visible:
                b_delete.name = 'Confirm Deletion'
                del_warn.visible = True
                b_cancel.visible = True
            else:
                old_options = wt_mc_proj.options.copy()
                old_options.remove(choice[0])

                wt_mc_proj.value = []
                wt_mc_proj.options = old_options

                ########################################
                # Do the actual project removal.
                ########################################
                proj = project(choice[0])
                try:
                    proj.remove(force=True)
                except FileNotFoundError:
                    print('The project or at least one of the directories does not exist.')
                    return

                # reset GUI
                b_delete.name = 'Remove Project'
                del_warn.visible = False
                b_cancel.visible = False

    def reassociate_experiments(event):

        try:
            proj_name_old = wt_mc_proj.value[0]
        except IndexError:
            proj_name_old = None

        proj_name_new = textbox.value
        if proj_name_new not in wt_mc_proj.options:
            print(
                "The new project name does not yet exist. You may click 'create Project' to create it and associate "
                "the selected experiments with this project")
            return

        if any(info_df.value.select == True):
            print('Reassociating experiments to new project')

            proj_old = project(proj_name_old)
            proj_new = project(proj_name_new)

            # first, remove from unassociated list:
            for exp_name in info_df.value.Name[info_df.value.select == True]:
                reassociate(proj_old, proj_new,
                            exp_name)  # this function changes all relevant paths, entries and moves files.

    def _reset_warning(event):
        # reset
        b_delete.name = 'Remove Experiment'
        del_warn.visible = False
        b_cancel.visible = False

    @pn.depends(wt_mc_proj.param.value, watch=True)
    def _update_info(selection):

        if len(selection) > 0:
            proj_name = selection[0]
            proj = project(proj_name)
            exp_list = proj.list_exp(verbose=False)
            info_panel.name = 'Experiments associated with this project'
            info_panel.value = str(len(exp_list))

            df = proj.provide_info()
        else:
            proj_name = None
            proj = project(proj_name)
            exp_list = list_unassociated_exp(verbose=False)
            info_panel.name = 'Experiments not associated with any project'
            info_panel.value = str(len(exp_list))
            df = proj.provide_info()

        info_df.value = df

    b_create.on_click(create_proj)
    b_rename.on_click(rename_proj)
    b_delete.on_click(remove_proj)
    b_cancel.on_click(_reset_warning)
    b_reassociate.on_click(reassociate_experiments)

    proj_row = pn.Row(pn.Column(wt_mc_proj, textbox, b_create, b_rename, b_delete, del_warn, b_cancel, b_reassociate),
                      pn.Column(info_panel, info_df), name='Project')

    return proj_row

class GUI:

    def __init__(self):
        super(GUI, self).__init__()

        # set paths
        self.home_path, self.db_path, self.run_path, self.archive_path, self.plot_path = wrftamer_paths()

        # wrftamer
        self.project = wt_proj_tab()
        self.experiment = self.wt_exp_tab()
        self.about = self.wt_about_tab()

        # wrfplotter
        self.stats = None
        self.obs_data = dict()
        self.mod_data = dict()
        self.map_cls = None

        # -----------------------------------------------------------------------------
        # TODO: make dynamic.
        self.list_of_obs = ['AV01', 'AV02', 'AV03', 'AV04', 'AV05', 'AV06',
                            'AV07', 'AV08', 'AV09', 'AV10', 'AV11', 'AV12',
                            'FINO1']
        self.dataset_dict = dict()
        self.dataset_dict['FINO1'] = 'FINO1'
        self.dataset_dict['FINOC'] = 'FINOC'
        for idx in range(1, 13):
            self.dataset_dict['AV' + str(idx).zfill(2)] = 'AV'
        # -----------------------------------------------------------------------------

        self.plottypes_avil = ['Timeseries', 'Profiles', 'Obs vs Mod', 'zt-Plot', 'Map']

        self.plot_panel = self.wp_create_plot_panel()
        self.menu1, self.menu2, self.menu_map = self.wp_create_menus()

        self._wp_update_plot()
        self.wp = pn.Row(self.menu1, pn.Column(self.menu2, self.plot_panel),name='WRFplotter')

        # Collect all Tabs
        self.view = pn.Tabs(self.project, self.experiment, self.wp, self.about)

    def wt_exp_tab(self, *args):

        ################################################################################################
        # menu
        ################################################################################################

        list_of_experiments = list_unassociated_exp(verbose=False)

        global mc_exp
        mc_exp = pn.widgets.MultiChoice(name='Choose Experiment', value=[''], options=list_of_experiments, height=75)

        exp_name_box = pn.widgets.TextInput(name='New Experiment Name', value='')

        b_create = pn.widgets.Button(name='Create Experiment', button_type='success')
        b_rename = pn.widgets.Button(name='Rename Experiment', button_type='warning')
        b_delete = pn.widgets.Button(name='Remove Experiment', button_type='danger')
        b_copy = pn.widgets.Button(name='Copy Experiment', button_type='primary')
        b_post = pn.widgets.Button(name='Postprocessing', button_type='primary')
        b_archive = pn.widgets.Button(name='Archive Experiment', button_type='primary')

        del_warn = pn.widgets.StaticText(name='Warning',
                                         value='This will delete all data of this experiment. Click again to proceed.',
                                         background='#ffcc00')
        del_warn.visible = False

        msg_procesing = pn.widgets.StaticText(name='Processing', value='Please wait for a moment.',
                                              background='#ffcc00')
        msg_procesing.visible = False

        b_cancel = pn.widgets.Button(name='Cancel', button_type='warning', visible=False)

        ################################################################################################
        # mainpage
        header = pn.widgets.StaticText(value='Select Configure File', background='#ffffff')
        file_input = pn.widgets.FileInput(name='Select Configure File', accept='.conf', multiple=False)

        comment_box = pn.widgets.TextInput(name='Comment', value='',
                                           placeholder='Add a brief description of your experiment here')

        default_message = 'To create an experiment, first create an Exp_name.conf file and select it. You may select' \
                          'an existing conf file and edit it here (if required). Per default, The name of the conf.file' \
                          'is used for the experiment name, but you may edit the name if you desire.' \
                          'Then, click "create experiment" to create a new experiment. You may also ' \
                          'copy-paste the content of a .conf file into this textbox. In any case, a new .conf file ' \
                          'will be stored in your experiment folder. '
        textfield = pn.widgets.input.TextAreaInput(name='Configure File', placeholder=default_message, height=800,
                                                   width=800)

        ################################################################################################

        def create_exp(event):

            try:
                proj_name = wt_mc_proj.value[0]
            except IndexError:
                proj_name = None

            exp_name = exp_name_box.value

            old_options = mc_exp.options.copy()

            if file_input.value is None:
                print('Please select a .conf file first')
                return
            else:
                # Now, I store the contents of either the file_input or the textfield (has priority) as a temporary
                # file. This file will be deleted later on. I need this file since the create.sh script is written
                # this way. It requires a file as input.

                configfile = self.db_path / '.temporary_configfile'
                fid = open(configfile, 'w')
                if textfield.value == '':
                    fid.write(file_input.value.decode())
                else:
                    fid.write(textfield.value)
                fid.close()

            if not re.match(r'^[A-Za-z0-9_-]+$', exp_name):
                print('Only alphanumeric values, underscore and dash are allowed in the experiment name')
                return
            elif exp_name in old_options:
                print('An experiment with this name already exists!')
                return
            else:
                old_options.append(exp_name)
                mc_exp.options = old_options

                ########################################
                # Do the actual Experiment creation.
                ########################################

                proj = project(proj_name)  # works even if proj_name is None > unassociated experiment
                exp = experiment(proj_name, exp_name)
                try:
                    start, end = exp.start_end(verbose=False)
                    proj.add_exp(exp_name, comment_box.value, start, end)
                    exp.create(configfile, namelisttemplate=None,
                               verbose=False)  # as of now, only allow the default namelist template.
                except FileExistsError:
                    print('An experiment with this name already exists. Use a different name or remove the directory '
                          'first.')

                os.remove(configfile)  # this was just a temporary file.

        def rename_exp(event):

            try:
                proj_name = wt_mc_proj.value[0]
            except IndexError:
                proj_name = None

            choice = mc_exp.value
            new_name = exp_name_box.value

            if len(choice) != 1 or new_name == '':
                print('Number of Experiments selected is not 1 or no new name set')
            else:
                exp_name = choice[0]

                old_options = mc_exp.options.copy()

                if new_name in old_options:
                    print('A project with this name already exists')
                else:
                    old_options.remove(exp_name)
                    old_options.append(new_name)

                    mc_exp.options = old_options
                    mc_exp.value = [new_name]

                    ########################################
                    # Do the actual Experiment renaming
                    ########################################
                    proj = project(proj_name)
                    exp = experiment(proj_name, exp_name)

                    try:
                        proj.rename_exp(exp_name, new_name, verbose=False)
                        exp.rename(new_name)
                    except FileExistsError:
                        print('An experiment with the new name already exists.')
                    except FileNotFoundError:
                        print('This experiment does not exist.')

        def remove_exp(event):

            try:
                proj_name = wt_mc_proj.value[0]
            except IndexError:
                proj_name = None

            choice = mc_exp.value

            if len(choice) == 1:

                exp_name = choice[0]

                if not del_warn.visible:
                    b_delete.name = 'Confirm Deletion'
                    del_warn.visible = True
                    b_cancel.visible = True
                else:
                    old_options = mc_exp.options.copy()
                    old_options.remove(exp_name)

                    mc_exp.value = []
                    mc_exp.options = old_options

                    ########################################
                    # Do the actual Experiment removal.
                    ########################################
                    proj = project(proj_name)
                    exp = experiment(proj_name, exp_name)

                    try:
                        proj.remove_exp(exp_name, force=True, verbose=False)
                        exp.remove(force=True)
                    except FileNotFoundError:
                        print('This experiment does not exist and cannot be removed')

                    # reset
                    b_delete.name = 'Remove Experiment'
                    del_warn.visible = False
                    b_cancel.visible = False

        def copy_exp(event):

            try:
                proj_name = wt_mc_proj.value[0]
            except IndexError:
                proj_name = None

            choice = mc_exp.value
            if len(choice) == 1:
                old_options = mc_exp.options.copy()

                exp_name = choice[0]
                new_exp_name = exp_name_box.value

                if not re.match(r'^[A-Za-z0-9_-]+$', new_exp_name):
                    print('Only alphanumeric values, underscore and dash are allowed in the experiment name')
                    return
                elif new_exp_name in old_options:
                    print('An experiment with this name already exists!')
                else:
                    old_options.append(exp_name_box.value)
                    mc_exp.options = old_options
                    ########################################
                    # Copy the actual Experiment.
                    ########################################

                    proj = project(proj_name)
                    exp = experiment(proj_name, exp_name)

                    try:
                        start, end = exp.start_end(verbose=False)
                        proj.add_exp(new_exp_name, comment_box.value, start, end)
                        exp.copy(new_exp_name)
                    except FileExistsError:
                        print('An experiment with the new name alreay exists.')
                    except FileNotFoundError:
                        print('This experiment does not exist.')

        def postprocess_exp(event):

            try:
                proj_name = wt_mc_proj.value[0]
            except IndexError:
                proj_name = None

            choices = mc_exp.value
            if len(choices) > 0:
                ########################################
                # Do the actual Experiment postprocessing constisting of:
                # 1. Check rsl file that the run is really complete
                # 2. Move data
                # 3. run tslist processing, if any tslist data exists.
                ########################################
                # This may may postprocess multiple experiments at a time

                msg_procesing.visible = True
                for exp_name in choices:
                    print('Processing:', exp_name)
                    exp = experiment(proj_name, exp_name)

                    try:
                        exp.move()
                        # I may want to make this dynamic later on
                        exp.process_tslist(location=None, domain=None, timeavg=[5, 10])
                    except FileNotFoundError:
                        print('The directory that contains the tsfiles does not exist.')

                msg_procesing.visible = False

        def archive_exp(event):

            keep_log = True  # I may want to add a switch later on?

            try:
                proj_name = wt_mc_proj.value[0]
            except IndexError:
                proj_name = None

            choices = mc_exp.value
            if len(choices) > 0:
                ########################################
                # Do the actual Experiment archiving:
                ########################################

                msg_procesing.visible = True

                for exp_name in choices:
                    print('Archiving:', exp_name)
                    exp = experiment(proj_name, exp_name)
                    exp.archive(keep_log=bool(keep_log))

                msg_procesing.visible = False

        def _reset_warning(event):
            # reset
            b_delete.name = 'Remove Experiment'
            del_warn.visible = False
            b_cancel.visible = False

        @pn.depends(file_input.param.filename, watch=True)  # do not use para.value as a trigger here.
        # Reason: value is set before filename. That would cause the second line to fail.
        def _update_textfield(selection):

            textfield.value = file_input.value.decode()
            exp_name_box.value = file_input.filename.split('.')[0]
            # Use the filename as the experiment name. The user may change that in the process.

        @pn.depends(wt_mc_proj.param.value, watch=True)
        def _update_exp_list(selection):
            if len(selection) == 1:
                proj_name = selection[0]
                proj = project(proj_name)

                new_options = proj.list_exp(verbose=False)

                mc_exp.options = new_options

            else:
                mc_exp.options = list_unassociated_exp(verbose=False)

        b_create.on_click(create_exp)
        b_rename.on_click(rename_exp)
        b_delete.on_click(remove_exp)

        b_copy.on_click(copy_exp)
        b_post.on_click(postprocess_exp)
        b_archive.on_click(archive_exp)

        b_cancel.on_click(_reset_warning)

        ################################################################################################

        menu = pn.Column(mc_exp, exp_name_box, b_create, b_rename, b_delete, del_warn, b_cancel, b_copy, b_post,
                         b_archive, name='Experiment')
        main = pn.Column(header, file_input, comment_box, textfield)

        exp_row = pn.Row(menu, main, name='Experiment')

        return exp_row

    def wt_about_tab(self):

        message = f'This is WRFtamer, Version {wrftamer.__version__}'

        text1 = pn.widgets.StaticText(name='Information', value=message, background='#ffffff')
        text2 = pn.widgets.StaticText(name='Your Tamer Path', value=self.db_path, background='#ffffff')
        text3 = pn.widgets.StaticText(name='Your run directory', value=self.run_path, background='#ffffff')
        text4 = pn.widgets.StaticText(name='Your archive directory', value=self.archive_path, background='#ffffff')
        text5 = pn.widgets.StaticText(name='Your plot directory', value=self.plot_path, background='#ffffff')

        about = pn.Column(text1, text2, text3, text4, text5, name='About')

        return about

    def wp_create_menus(self):

        global but_dev, mc_proj, mc_exp, sel_dom, sel_loc, sel_obs, sel_ave, time_to_plot, chk_static
        global sel_var, sel_lev, png_pane, but_right, but_left

        # Menu 1
        list_of_projects = list_projects(verbose=False)
        list_of_experiments = list_unassociated_exp(verbose=False)

        list_of_domains = ['d01', 'd02', 'd03']  # make dynamic in the future
        list_of_locs = ['FINO', 'AV01', 'AV02', 'AV03', 'AV04', 'AV05', 'AV06', 'AV07', 'AV08', 'AV09', 'AV10',
                        'AV11', 'AV12']  # TODO: make dynamic, merge with list_of_obs

        # dynamically remove tslist for Map? # Removed 'aux' from the list for now. I never use it in ParkCast.
        list_of_obs = ['FINO1', 'FINOC', 'AV01', 'AV02', 'AV03', 'AV04', 'AV05', 'AV06', 'AV07', 'AV08', 'AV09', 'AV10',
                       'AV11', 'AV12']  # TODO: make dynamic

        list_of_ave_windows = ['raw', '5 min Ave', '10 min Ave', '30 min Ave']

        mc_proj = pn.widgets.MultiChoice(name='Choose Project', max_items=1, value=[], options=list_of_projects,
                                         height=75)
        mc_exp = pn.widgets.MultiChoice(name='Choose Experiment', value=[''], options=list_of_experiments, height=200)

        sel_dom = pn.widgets.Select(name='Domain', options=list_of_domains)
        sel_loc = pn.widgets.Select(name='Model data at', options=list_of_locs)
        sel_obs = pn.widgets.Select(name='Observation at', options=list_of_obs)
        but_dev = pn.widgets.Button(name='Sonic', button_type='default')
        sel_ave = pn.widgets.Select(name='Averaging', options=list_of_ave_windows)

        # this is just a random default. Must pick reasonable values for each proj_name!
        time_values = (dt.datetime(2020, 5, 1, 0, 0), dt.datetime(2020, 5, 6, 0, 0))
        # is updated at exp_selection.
        # question: what happens if I have multiple exps with different time limits?
        time_to_plot = pn.widgets.DatetimeInput(name='Datetime Input', value=time_values[0])
        chk_static = pn.widgets.Checkbox(name='Static Plots')

        but_load = pn.widgets.Button(name='Load Data', button_type='default')
        progress = pn.indicators.Progress(name='Progress', value=0, width=300, visible=False)
        progress.visible = False

        # Menu2
        _dict_of_vars_per_plottype = get_vars_per_plottype()  # prefefined. Not dynamically
        _dict_of_levs_per_plottype_and_var = get_lev_per_plottype_and_var()  # prefefined. Not dynamically

        sel_var = pn.widgets.Select(name='Variable', options=_dict_of_vars_per_plottype['Timeseries'])  # default
        sel_lev = pn.widgets.Select(name='Level', options=_dict_of_levs_per_plottype_and_var['Timeseries'][
            'WSP_Sonic'])  # default values

        sel_store = pn.widgets.Select(name='data type', options=['markdown', 'csv'])
        but_store = pn.widgets.Button(name='Save Table', button_type='default', margin=[23, 10])

        alert1 = pn.pane.Alert('Time series data should be reloaded', alert_type="danger")
        alert1.visible = False

        alert2 = pn.pane.Alert('Map data may have to be reloaded', alert_type="warning")
        alert2.visible = False

        # Map Menu
        but_left = pn.widgets.Button(name='\u25c0', width=50)
        but_right = pn.widgets.Button(name='\u25b6', width=50)
        png_pane = pn.pane.PNG(None, width=500)

        # ---------------------------------------------------------------------------------------------------
        # ------------------------------ Functions that interact with widgets. ------------------------------
        # ---------------------------------------------------------------------------------------------------
        def _toggle_dev(event):

            if but_dev.name == 'Sonic':
                but_dev.name = 'Analog'
            else:
                but_dev.name = 'Sonic'

        @pn.depends(mc_proj.param.value, watch=True)
        def _update_exp_list(selection):
            if len(selection) == 1:
                proj_name = selection[0]
                proj = project(proj_name)

                new_options = proj.list_exp(verbose=False)
                mc_exp.options = new_options

            else:
                mc_exp.options = list_unassociated_exp(verbose=False)

        @pn.depends(mc_exp.param.value, watch=True)
        def _update_ttp(selection):  # time to plot

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            try:
                exp_name = selection[0]
                # for now, always use the first one. In the future, select all and find min,max.

                exp = experiment(proj_name, exp_name)
                time_values = exp.start_end(False)
                time_to_plot.value = time_values[0]
            except IndexError:
                pass

        @pn.depends(mc_proj.param.value, sel_dom.param.value,
                    but_dev.param.name, sel_ave.param.value, watch=True)
        def _reload_watcher1(proj, dom, dev, ave):
            # Watches for changes in relevant parameters and indicates that a reload is needed
            alert1.visible = True

        @pn.depends(mc_proj.param.value, mc_exp.param.value, sel_dom.param.value,
                    sel_var.param.value, sel_lev.param.value, watch=True)
        def _reload_watcher2(proj, exp_names, dom, var, lev):
            # Watches for changes in relevant parameters and indicates that a reload is needed
            # This is for maps
            alert2.visible = True

        def _load_data(event):

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            plottype = self.plottypes_avil[self.plot_panel.active]
            dom = sel_dom.value

            if plottype in ['Timeseries', 'Profiles', 'Obs vs Mod', 'zt-Plot']:

                ave = sel_ave.value
                dev = but_dev.name
                ttp = time_to_plot.value

                infos = set_infos(proj_name=proj_name, domain=dom, ave=ave, device=dev, time_to_plot=ttp)

                progress.visible = True

                # --------------------------------------
                #                Obs
                # --------------------------------------
                self.obs_data = dict()  # to make sure that no nonesens is kept in memory
                progress.bar_color = 'info'
                for idx, obs in enumerate(self.list_of_obs):
                    dataset = self.dataset_dict[obs]
                    load_obs_data(self.obs_data, obs, dataset, **infos)
                    progress_value = int(100 * (idx + 1) / len(self.list_of_obs))
                    progress.value = progress_value

                # --------------------------------------
                #                Mod
                # --------------------------------------
                self.mod_data = dict()  # to make sure that no nonesens is kept in memory
                progress.bar_color = 'primary'
                progress.value = 0
                try:
                    proj_name = infos['proj_name']
                except KeyError:
                    proj_name = None

                proj = project(proj_name)
                list_of_exps = proj.list_exp(verbose=False)

                for idx, exp_name in enumerate(list_of_exps):
                    load_mod_data(self.mod_data, exp_name, **infos)
                    progress_value = int(100 * (idx + 1) / len(list_of_exps))
                    progress.value = progress_value

                progress.visible = False
                but_load.button_type = 'success'
                alert1.visible = False

            elif plottype == 'Map':
                # --------------------------------------
                #                Map
                # --------------------------------------
                self.map_cls = None
                try:
                    var = sel_var.value
                    lev = sel_lev.value

                    exp_name = mc_exp.value[0]
                    exp = experiment(proj_name, exp_name)
                    i_path = exp.exp_path / 'out'

                    # poi_file = os.environ['WRFTAMER_POI_FILE'] # Future
                    # testing.
                    #TODO: generalize!
                    poi_file = '/home/daniel/projects/parkcast/repos/WRFtamer/wrftamer/resources/Koordinaten_Windpark.csv'
                    poi = pd.read_csv(poi_file, delimiter=';')
                    self.map_cls = Map(poi=poi, intermediate_path=i_path)
                    self.map_cls.load_intermediate(dom, var, lev, '*')

                    alert2.visible = False
                except Exception as e:
                    print(e)
                    print(i_path, dom, var, lev)
            else:
                pass

        @pn.depends(self.plot_panel.param.active, watch=True)  # udating widgets related to table storing
        def _update_store(active):
            if active in [0, 2]:
                sel_store.disabled = False
                but_store.disabled = False
            else:
                sel_store.disabled = True
                but_store.disabled = True

        @pn.depends(self.plot_panel.param.active, watch=True)
        def _update_sel_var(active):
            plottype = self.plottypes_avil[active]
            sel_var.options = _dict_of_vars_per_plottype[plottype]

        @pn.depends(self.plot_panel.param.active, sel_var.param.value, but_dev.param.name, watch=True)
        def _update_sel_lev(active, var, device):

            if var in ['WSP', 'DIR', 'WSP and DIR', 'WSP and PT'] and active in [0, 2]:
                tmp_var = var + '_' + device
            else:
                tmp_var = var

            plottype = self.plottypes_avil[active]

            if active in [1]:
                sel_lev.disabled = True
                sel_lev.options = []
            else:
                sel_lev.disabled = False
                sel_lev.options = _dict_of_levs_per_plottype_and_var[plottype][tmp_var]

        def _store_table(event):

            but_store.button_type = 'warning'
            extension = sel_store.value
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

            but_store.button_type = 'success'

        def _change_pic_left(event):
            current_filename = Path(png_pane.object)  # The filename must be Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png
            new_filename = get_newfilename_from_old(current_filename, -10)  # For now, delta_t is fixed to 10 minuts
            png_pane.object = str(new_filename)

        def _change_pic_right(event):
            current_filename = Path(png_pane.object)  # The filename must be Map_d0X_VAR_YYYYMMDD_HHMMSS_mlY.png
            new_filename = get_newfilename_from_old(current_filename, +10)  # For now, delta_t is fixed to 10 minuts
            png_pane.object = str(new_filename)

        # Button click events
        but_dev.on_click(_toggle_dev)
        but_load.on_click(_load_data)
        but_store.on_click(_store_table)
        but_left.on_click(_change_pic_left)
        but_right.on_click(_change_pic_right)

        menu1 = pn.Column(mc_proj, mc_exp, sel_dom, sel_loc, sel_obs, but_dev, sel_ave, time_to_plot, chk_static,
                          progress, but_load)
        menu2 = pn.Row(
            pn.Column(pn.Row(sel_var, sel_lev), pn.Row(sel_store, but_store)),
            pn.Column(alert1, alert2)
        )

        menu_map = pn.Column(png_pane, pn.Row(but_left, but_right))

        return menu1, menu2, menu_map

    def wp_create_plot_panel(self):
        # Creates an empty plot panel
        tabs = []
        for plottype in self.plottypes_avil:
            tmp = (plottype, None)
            tabs.append(tmp)

        tabs = tuple(tabs)
        panel = pn.Tabs(*tabs)

        return panel

    def _wp_update_plot(self):

        @pn.depends(self.plot_panel.param.active,
                    mc_proj.param.value, mc_exp.param.value, sel_dom.param.value, sel_loc.param.value,
                    sel_obs.param.value, but_dev.param.name, sel_ave.param.value,
                    sel_var.param.value, sel_lev.param.value, time_to_plot.param.value, chk_static.param.value,
                    watch=True)
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
                        # figure = create_mpl_plot(obs_data, mod_data, infos)
                        figure = error_message('Static plots not yet implemented.')
                        self.stats = None
                    else:
                        figure, self.stats = create_hv_plot(infos, obs_data=self.obs_data, mod_data=self.mod_data)

                elif plottype == 'Map':

                    if static_plots:

                        exp = experiment(proj_name, exp_list[0])
                        timestamp = ttp.strftime('%Y%m%d_%H%M%S')
                        filename = exp.exp_path / f'plot/Map_{dom}_{var}_{timestamp}_ml{lev}.png'

                        if filename.is_file():
                            png_pane.object = str(filename)
                            figure = self.menu_map
                        else:
                            figure = error_message2(filename)
                    else:
                        try:
                            # This is not very nice, but the best I can do right now.
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

a = GUI()
a.view.servable("WRFtamer")