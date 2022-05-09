import panel as pn
import re
from wrftamer.gui.gui_base import gui_base
from wrftamer.main import project, list_projects, list_unassociated_exp, reassociate

tabulator_formatters = {"select": {"type": "tickCross"}}


class proj_tab(gui_base):
    """
    Manual tests of gui sucessful (WRFTamer Version 1.1)
    """

    def __init__(self):
        super(proj_tab, self).__init__()

        list_of_projects = list_projects(verbose=False)
        list_of_experiments = list_unassociated_exp(verbose=False)

        self.mc_proj = pn.widgets.MultiChoice(
            name="Choose Project",
            max_items=1,
            value=[],
            options=list_of_projects,
            height=75,
        )

        self.textbox = pn.widgets.TextInput(name="New Project Name", value="")

        self.b_create = pn.widgets.Button(name="Create Project", button_type="success")
        self.b_rename = pn.widgets.Button(name="Rename Project", button_type="warning")
        self.b_delete = pn.widgets.Button(name="Remove Project", button_type="danger")
        self.b_reassociate = pn.widgets.Button(
            name="Reassociate Experiments", button_type="primary"
        )

        self.del_warn = pn.widgets.StaticText(
            name="Warning",
            value="This will delete all data of this project. Click again to proceed.",
            background="#ffcc00",
        )
        self.del_warn.visible = False

        self.b_cancel = pn.widgets.Button(
            name="Cancel", button_type="warning", visible=False
        )

        self.info_panel = pn.widgets.StaticText(
            name="Experiments not associated with any project",
            value=str(len(list_of_experiments)),
            background="#ffffff",
        )

        proj = project(None)
        df = proj.exp_provide_info()
        self.info_df = pn.widgets.Tabulator(df, formatters=tabulator_formatters, height=600)

        self.b_create.on_click(self.create_proj)
        self.b_rename.on_click(self.rename_proj)
        self.b_delete.on_click(self.remove_proj)
        self.b_cancel.on_click(self._reset_warning)
        self.b_reassociate.on_click(self.reassociate_experiments)

        @pn.depends(self.mc_proj.param.value, watch=True)
        def _update_info(selection):

            if len(selection) > 0:
                proj_name = selection[0]
                proj = project(proj_name)
                exp_list = proj.list_exp(verbose=False)
                self.info_panel.name = "Experiments associated with this project"
                self.info_panel.value = str(len(exp_list))
            else:
                proj_name = None
                proj = project(proj_name)
                exp_list = list_unassociated_exp(verbose=False)
                self.info_panel.name = "Experiments not associated with any project"
                self.info_panel.value = str(len(exp_list))

            df = proj.exp_provide_info()
            self.info_df.value = df

    # noinspection PyUnusedLocal
    def create_proj(self, event):

        old_options = self.mc_proj.options.copy()
        proj_name = self.textbox.value

        if not re.match(r"^[A-Za-z0-9_-]+$", self.textbox.value):
            print(
                "Only alphanumeric values, underscore and dash are allowed in the project name"
            )
            return
        elif self.textbox.value in old_options:
            print("A project with this name already exists!")
            return
        else:
            old_options.append(self.textbox.value)
            self.mc_proj.options = old_options

            ########################################
            # Do the actual project creation.
            ########################################
            proj = project(proj_name)

            try:
                proj.create()
            except FileExistsError:
                print(
                    "A project with this name already exists. Remove project or choose a different name"
                )
                return

            if any(self.info_df.value.select):
                print("Combining unassociated experiments to new project")

                # Now, move the selected directories, associate with the new project and remove from unassociated
                # list. Right now, I cannot reassociate an experiment from project1 to project2. Only from
                # unassociated to associated.

                try:
                    proj_name_old = self.mc_proj.value[0]
                except IndexError:
                    proj_name_old = None

                proj_old = project(proj_name_old)

                # first, remove from unassociated list:
                for exp_name in self.info_df.value.Name[self.info_df.value.select]:
                    reassociate(
                        proj_old, proj, exp_name
                    )  # this function changes all relevant paths, entries and
                    # moves files.

    # noinspection PyUnusedLocal
    def rename_proj(self, event):

        choice = self.mc_proj.value
        new_name = self.textbox.value

        if len(choice) > 0 and new_name != "":
            old_options = self.mc_proj.options.copy()

            if new_name in old_options:
                print("A project with this name already exists")
            else:
                old_options.remove(choice[0])
                old_options.append(new_name)

                ########################################
                # Do the actual project renaming
                ########################################
                proj = project(choice[0])
                proj.rename(new_name)

                # Change widgets of gui
                self.mc_proj.options = old_options
                self.mc_proj.value = [new_name]

    # noinspection PyUnusedLocal
    def remove_proj(self, event):

        choice = self.mc_proj.value

        if len(choice) > 0:

            if not self.del_warn.visible:
                self.b_delete.name = "Confirm Deletion"
                self.del_warn.visible = True
                self.b_cancel.visible = True
            else:
                old_options = self.mc_proj.options.copy()
                old_options.remove(choice[0])

                self.mc_proj.value = []
                self.mc_proj.options = old_options

                ########################################
                # Do the actual project removal.
                ########################################
                proj = project(choice[0])
                try:
                    proj.remove(force=True)
                except FileNotFoundError:
                    print(
                        "The project or at least one of the directories does not exist."
                    )
                    return

                # reset GUI
                self.b_delete.name = "Remove Project"
                self.del_warn.visible = False
                self.b_cancel.visible = False

    # noinspection PyUnusedLocal
    def reassociate_experiments(self, event):

        try:
            proj_name_old = self.mc_proj.value[0]
        except IndexError:
            proj_name_old = None

        proj_name_new = self.textbox.value
        if proj_name_new not in self.mc_proj.options:
            print(
                "The new project name does not yet exist. You may click 'create Project' to create it and associate "
                "the selected experiments with this project"
            )
            return

        if any(self.info_df.value.select):
            print("Reassociating experiments to new project")

            proj_old = project(proj_name_old)
            proj_new = project(proj_name_new)

            # first, remove from unassociated list:
            for exp_name in self.info_df.value.Name[self.info_df.value.select]:
                reassociate(
                    proj_old, proj_new, exp_name
                )  # this function changes all relevant paths, entries and moves files.

    # noinspection PyUnusedLocal
    def _reset_warning(self, event):
        # reset
        self.b_delete.name = "Remove Experiment"
        self.del_warn.visible = False
        self.b_cancel.visible = False

    def view(self):

        proj_row = pn.Row(
            pn.Column(
                self.mc_proj,
                self.textbox,
                self.b_create,
                self.b_rename,
                self.b_delete,
                self.del_warn,
                self.b_cancel,
                self.b_reassociate,
            ),
            pn.Column(self.info_panel, self.info_df),
            name="Project",
        )

        return proj_row
