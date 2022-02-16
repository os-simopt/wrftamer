from wrftamer.project_management import project, list_projects, list_unassociated_exp, reassociate
from wrftamer.experiment_management import experiment

import os
import panel as pn
import re
from wrftamer.wrftamer_paths import wrftamer_paths


pn.extension('tabulator')
# pn.extension(loading_spinner='dots', loading_color='#00aa41')
# pn.param.ParamMethod.loading_indicator = True

tabulator_formatters = {
    'select': {'type': 'tickCross'}
}


def proj_tab(*args):
    list_of_projects = list_projects(verbose=False)
    list_of_experiments = list_unassociated_exp(verbose=False)

    global mc_proj
    mc_proj = pn.widgets.MultiChoice(name='Choose Project', max_items=1, value=[], options=list_of_projects,
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

        old_options = mc_proj.options.copy()
        proj_name = textbox.value

        if not re.match(r'^[A-Za-z0-9_-]+$', textbox.value):
            print('Only alphanumeric values, underscore and dash are allowed in the project name')
            return
        elif textbox.value in old_options:
            print('A project with this name already exists!')
            return
        else:
            old_options.append(textbox.value)
            mc_proj.options = old_options

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
                    proj_name_old = mc_proj.value[0]
                except IndexError:
                    proj_name_old = None

                proj_old = project(proj_name_old)

                # first, remove from unassociated list:
                for exp_name in info_df.value.Name[info_df.value.select == True]:
                    reassociate(proj_old, proj, exp_name)  # this function changes all relevant paths, entries and
                    # moves files.

    def rename_proj(event):

        choice = mc_proj.value
        new_name = textbox.value

        if len(choice) > 0 and new_name != '':
            old_options = mc_proj.options.copy()

            if new_name in old_options:
                print('A project with this name already exists')
            else:
                old_options.remove(choice[0])
                old_options.append(new_name)

                mc_proj.options = old_options
                mc_proj.value = [new_name]

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

        choice = mc_proj.value

        if len(choice) > 0:

            if not del_warn.visible:
                b_delete.name = 'Confirm Deletion'
                del_warn.visible = True
                b_cancel.visible = True
            else:
                old_options = mc_proj.options.copy()
                old_options.remove(choice[0])

                mc_proj.value = []
                mc_proj.options = old_options

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
            proj_name_old = mc_proj.value[0]
        except IndexError:
            proj_name_old = None

        proj_name_new = textbox.value
        if proj_name_new not in mc_proj.options:
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

    @pn.depends(mc_proj.param.value, watch=True)
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

    proj_row = pn.Row(pn.Column(mc_proj, textbox, b_create, b_rename, b_delete, del_warn, b_cancel, b_reassociate),
                      pn.Column(info_panel, info_df), name='Project')

    return proj_row


def exp_info_tab():
    text1 = pn.widgets.StaticText(name='Information on experiment', value='', background='#ffffff')
    text2 = pn.widgets.StaticText(name='Info', value='', background='#ffffff')

    message = 'Display disk use, runtime, status (created, ready-to-run, running, complete, postprocessed, archived, ' \
              'failed '
    text3 = pn.widgets.StaticText(name='Ideas', value=message, background='#ffffff')

    @pn.depends(mc_exp.param.value, watch=True)
    def _update_infos(selection):

        message = 'Plots. Which plot is the best one? '
        if len(selection) == 1:
            text1.value = selection[0]
        else:
            text1.value = ''
        text2.value = message

    exp_info = pn.Column(text1, text2, text3, name='Exp info')

    return exp_info


class GUI:
    def __init__(self):
        super(GUI, self).__init__()

        # set paths
        self.home_path, self.db_path, self.run_path, self.archive_path = wrftamer_paths()

        self.project = proj_tab()
        self.experiment = self.exp_tab()
        self.about = self.about_tab()
        self.exp_info = exp_info_tab()

    def exp_tab(self, *args):

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
                proj_name = mc_proj.value[0]
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
                proj_name = mc_proj.value[0]
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
                proj_name = mc_proj.value[0]
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
                proj_name = mc_proj.value[0]
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
                proj_name = mc_proj.value[0]
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
                proj_name = mc_proj.value[0]
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

        @pn.depends(mc_proj.param.value, watch=True)
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

    def about_tab(self):

        message = 'This is WRF-Tamer Version 1.0'

        text1 = pn.widgets.StaticText(name='Information', value=message, background='#ffffff')
        text2 = pn.widgets.StaticText(name='Your Tamer Path', value=self.db_path, background='#ffffff')
        text3 = pn.widgets.StaticText(name='Your run directory', value=self.run_path, background='#ffffff')
        text4 = pn.widgets.StaticText(name='Your archive directory', value=self.archive_path, background='#ffffff')

        about = pn.Column(text1, text2, text3, text4, name='About')

        return about


a = GUI()
pn.Tabs(a.project, a.experiment, a.exp_info, a.about).servable("WRF Tamer")
