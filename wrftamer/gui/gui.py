import panel as pn

from wrftamer.gui.proj_tab import proj_tab
from wrftamer.gui.exp_tab import exp_tab
from wrftamer.gui.about_tab import about_tab
from wrftamer.gui.wrfplotter_tab import wrfplotter_tab

pn.extension("tabulator")
tabulator_formatters = {"select": {"type": "tickCross"}}


class GUI:
    def __init__(self):
        self.project = proj_tab()
        self.experiment = exp_tab(self.project.mc_proj)
        self.about = about_tab()
        self.wp = wrfplotter_tab()

    def view(self):
        all_tabs = pn.Tabs(
            self.project.view(),
            self.experiment.view(),
            self.wp.view(),
            self.about.view(),
        )

        return all_tabs


a = GUI()
a.view().servable("wrftamer")

# TODO: what happens if no observations exists? What are the levels then?
# TODO: add windroses
# TODO: add histogramm plots.
# TODO: add etalevel program
# TODO: add domänenübersicht.
# TODO: most likely, I need to improve the docs on Preparing obs.
