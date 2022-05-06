import os
import re
import panel as pn

from wrftamer.main import project, list_unassociated_exp
from wrftamer.gui.gui_base import gui_base


class exp_tab(gui_base):
    """
    Manual tests of gui sucessful (WRFTamer Version 1.1)
    """

    def __init__(self, mc_proj):
        super(exp_tab, self).__init__()

        ################################################################################################
        # menu
        ################################################################################################

        self.list_of_experiments = list_unassociated_exp(verbose=False)

        self.mc_exp = pn.widgets.MultiChoice(
            name="Choose Experiment",
            value=[""],
            options=self.list_of_experiments,
            height=75,
        )

        self.exp_name_box = pn.widgets.TextInput(name="New Experiment Name", value="")

        self.b_create = pn.widgets.Button(
            name="Create Experiment", button_type="success"
        )
        self.b_rename = pn.widgets.Button(
            name="Rename Experiment", button_type="warning"
        )
        self.b_delete = pn.widgets.Button(
            name="Remove Experiment", button_type="danger"
        )
        self.b_copy = pn.widgets.Button(name="Copy Experiment", button_type="primary")
        self.b_post = pn.widgets.Button(name="Postprocessing", button_type="primary")
        self.b_archive = pn.widgets.Button(
            name="Archive Experiment", button_type="primary"
        )

        self.del_warn = pn.widgets.StaticText(
            name="Warning",
            value="This will delete all data of this experiment. Click again to "
            "proceed.",
            background="#ffcc00",
        )
        self.del_warn.visible = False

        self.msg_procesing = pn.widgets.StaticText(
            name="Processing", value="Please wait for a moment.", background="#ffcc00"
        )
        self.msg_procesing.visible = False

        self.b_cancel = pn.widgets.Button(
            name="Cancel", button_type="warning", visible=False
        )

        ################################################################################################
        # mainpage
        self.header = pn.widgets.StaticText(
            value="Select Configure File", background="#ffffff"
        )
        self.file_input = pn.widgets.FileInput(
            name="Select Configure File", accept=".yaml", multiple=False
        )

        self.comment_box = pn.widgets.TextInput(
            name="Comment",
            value="",
            placeholder="Add a brief description of your experiment here",
        )

        default_message = (
            "To create an experiment, first create an configure.yaml file and select it. You may select"
            "an existing conf file and edit it here. Per default, the name of the configure.yaml"
            "file is used for the experiment name, but you may edit the name if you desire a different"
            'name. Then, click "create experiment" to create a new experiment. You may also '
            "copy-paste the content of a configure.yaml file into this textbox. In any case, a new "
            "configure.yaml file will be stored in your experiment folder."
        )

        self.textfield = pn.widgets.input.TextAreaInput(
            name="Configure File", placeholder=default_message, height=800, width=800
        )

        ################################################################################################

        # noinspection PyUnusedLocal
        def create_exp(event):

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            exp_name = self.exp_name_box.value

            old_options = self.mc_exp.options.copy()

            if self.file_input.value is None:
                print("Please select a configure file first")
                return
            else:
                # Now, I store the contents of either the file_input or the textfield (has priority) as a temporary
                # file. This file will be deleted later on. I need this file since the create.sh script is written
                # this way. It requires a file as input.

                configfile = self.db_path / ".temporary_configfile"
                fid = open(configfile, "w")
                if self.textfield.value == "":
                    fid.write(self.file_input.value.decode())
                else:
                    fid.write(self.textfield.value)
                fid.close()

            if not re.match(r"^[A-Za-z0-9_-]+$", exp_name):
                print(
                    "Only alphanumeric values, underscore and dash are allowed in the experiment name"
                )
                return
            elif exp_name in old_options:
                print("An experiment with this name already exists!")
                return
            else:
                old_options.append(exp_name)
                self.mc_exp.options = old_options

                ########################################
                # Do the actual Experiment creation.
                ########################################

                # works even if proj_name is None > unassociated experiment
                proj = project(proj_name)
                try:
                    proj.exp_create(
                        exp_name,
                        self.comment_box.value,
                        configfile,
                        namelisttemplate=None,
                        verbose=False,
                    )

                except FileExistsError:
                    print("An experiment with this name already exists.")
                    print("Use a different name or remove the directory first.")

                os.remove(configfile)  # this was just a temporary file.

        # noinspection PyUnusedLocal
        def rename_exp(event):

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            choice = self.mc_exp.value
            new_name = self.exp_name_box.value

            if len(choice) != 1 or new_name == "":
                print("Number of Experiments selected is not 1 or no new name set")
            else:
                exp_name = choice[0]

                old_options = self.mc_exp.options.copy()

                if new_name in old_options:
                    print("A project with this name already exists")
                else:
                    old_options.remove(exp_name)
                    old_options.append(new_name)

                    self.mc_exp.options = old_options
                    self.mc_exp.value = [new_name]

                    ########################################
                    # Do the actual Experiment renaming
                    ########################################
                    proj = project(proj_name)
                    try:
                        proj.exp_rename(exp_name, new_name, verbose=False)
                    except FileExistsError:
                        print("An experiment with the new name already exists.")
                    except FileNotFoundError:
                        print("This experiment does not exist.")

        # noinspection PyUnusedLocal
        def remove_exp(event):

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            choice = self.mc_exp.value

            if len(choice) == 1:

                exp_name = choice[0]

                if not self.del_warn.visible:
                    self.b_delete.name = "Confirm Deletion"
                    self.del_warn.visible = True
                    self.b_cancel.visible = True
                else:
                    old_options = self.mc_exp.options.copy()
                    old_options.remove(exp_name)

                    self.mc_exp.value = []
                    self.mc_exp.options = old_options

                    ########################################
                    # Do the actual Experiment removal.
                    ########################################
                    proj = project(proj_name)

                    try:
                        proj.exp_remove(exp_name, force=True, verbose=False)
                    except FileNotFoundError:
                        print("This experiment does not exist and cannot be removed")

                    # reset
                    self.b_delete.name = "Remove Experiment"
                    self.del_warn.visible = False
                    self.b_cancel.visible = False

        # noinspection PyUnusedLocal
        def copy_exp(event):

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            choice = self.mc_exp.value
            if len(choice) == 1:
                old_options = self.mc_exp.options.copy()

                exp_name = choice[0]
                new_exp_name = self.exp_name_box.value

                if not re.match(r"^[A-Za-z0-9_-]+$", new_exp_name):
                    print(
                        "Only alphanumeric values, underscore and dash are allowed in the experiment name"
                    )
                    return
                elif new_exp_name in old_options:
                    print("An experiment with this name already exists!")
                else:
                    old_options.append(self.exp_name_box.value)
                    self.mc_exp.options = old_options
                    ########################################
                    # Copy the actual Experiment.
                    ########################################

                    proj = project(proj_name)

                    try:
                        proj.exp_copy(
                            exp_name,
                            new_exp_name,
                            self.comment_box.value,
                            verbose=False,
                        )
                    except FileExistsError:
                        print("An experiment with the new name alreay exists.")
                    except FileNotFoundError:
                        print("This experiment does not exist.")

        # noinspection PyUnusedLocal
        def postprocess_exp(event):

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            choices = self.mc_exp.value
            if len(choices) > 0:
                ########################################
                # Do the actual Experiment postprocessing according to the postprocessing protocol, as defined
                # in the configure.yaml file.

                # This routine may may postprocess multiple experiments sequentially.
                ########################################

                self.msg_procesing.visible = True
                for exp_name in choices:
                    print("Processing:", exp_name)
                    proj = project(proj_name)
                    proj.exp_run_postprocessing_protocol(exp_name, verbose=False)

                self.msg_procesing.visible = False

        # noinspection PyUnusedLocal
        def archive_exp(event):

            keep_log = True  # I may want to add a switch later on?

            try:
                proj_name = mc_proj.value[0]
            except IndexError:
                proj_name = None

            choices = self.mc_exp.value
            if len(choices) > 0:
                ########################################
                # Do the actual Experiment archiving:
                ########################################

                self.msg_procesing.visible = True

                for exp_name in choices:
                    print("Archiving:", exp_name)
                    proj = project(proj_name)
                    proj.exp_archive(exp_name, keep_log=bool(keep_log), verbose=False)

                self.msg_procesing.visible = False

        # noinspection PyUnusedLocal
        def _reset_warning(event):
            # reset
            self.b_delete.name = "Remove Experiment"
            self.del_warn.visible = False
            self.b_cancel.visible = False

        # noinspection PyUnusedLocal
        @pn.depends(
            self.file_input.param.filename, watch=True
        )  # do not use para.value as a trigger here.
        # Reason: value is set before filename. That would cause the second line to fail.
        def _update_textfield(selection):

            self.textfield.value = self.file_input.value.decode()
            self.exp_name_box.value = self.file_input.filename.split(".")[0]
            # By default, use the filename as the experiment name. The user may change this manually

        @pn.depends(mc_proj.param.value, watch=True)
        def _update_exp_list(selection):
            if len(selection) == 1:
                proj_name = selection[0]
                proj = project(proj_name)

                new_options = proj.list_exp(verbose=False)

                self.mc_exp.options = new_options

            else:
                self.mc_exp.options = list_unassociated_exp(verbose=False)

        self.b_create.on_click(create_exp)
        self.b_rename.on_click(rename_exp)
        self.b_delete.on_click(remove_exp)

        self.b_copy.on_click(copy_exp)
        self.b_post.on_click(postprocess_exp)
        self.b_archive.on_click(archive_exp)

        self.b_cancel.on_click(_reset_warning)

    ################################################################################################
    def view(self):

        menu = pn.Column(
            self.mc_exp,
            self.exp_name_box,
            self.b_create,
            self.b_rename,
            self.b_delete,
            self.del_warn,
            self.b_cancel,
            self.b_copy,
            self.b_post,
            self.b_archive,
            name="Experiment",
        )
        main = pn.Column(self.header, self.file_input, self.comment_box, self.textfield)

        exp_row = pn.Row(menu, main, name="Experiment")

        return exp_row
