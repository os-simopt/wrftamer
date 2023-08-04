import panel as pn

from gui.proj_tab import proj_tab
from gui.exp_tab import exp_tab
from gui.about_tab import about_tab

from gui.wrfplotter_tab import use_wrfplotter
if use_wrfplotter:
    from gui.wrfplotter_tab import wrfplotter_tab


pn.extension("tabulator")
tabulator_formatters = {"select": {"type": "tickCross"}}


class GUI:
    def __init__(self):
        self.project = proj_tab()
        self.experiment = exp_tab(self.project.mc_proj)
        self.about = about_tab()
        if use_wrfplotter:
            self.wp = wrfplotter_tab()
        else:
            self.wp = None

    def view(self):

        if use_wrfplotter:
            all_tabs = pn.Tabs(
                self.project.view(),
                self.experiment.view(),
                self.wp.view(),
                self.about.view()
            )
        else:
            all_tabs = pn.Tabs(
                self.project.view(),
                self.experiment.view(),
                self.about.view()
            )

        return all_tabs


a = GUI()
a.view().servable("WRFtamer")

# TODO (for Next Version):
# - add etalevel program
# - add domänenübersicht.
