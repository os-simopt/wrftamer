import os
import wrftamer
from wrftamer.gui.gui_base import path_base
import panel as pn


class about_tab(path_base):
    """
    Manual tests of gui sucessful (WRFTamer Version 1.1)
    """

    def __init__(self):
        super(about_tab, self).__init__()

        message = f"WRFtamer, Version {wrftamer.__version__}"

        self.text1 = pn.widgets.StaticText(name="Information", value=message, background="#ffffff")
        self.text2 = pn.widgets.StaticText(name="Your Tamer Path", value=self.db_path, background="#ffffff")
        self.text3 = pn.widgets.StaticText(name="Your run directory", value=self.run_path, background="#ffffff")
        self.text4 = pn.widgets.StaticText(name="Your archive directory", value=self.archive_path, background="#ffffff")
        self.text5 = pn.widgets.StaticText(name="Your plot directory", value=self.plot_path, background="#ffffff")
        self.poi_text = pn.widgets.StaticText(name="Your poi file", value=self.poi_file, background="#ffffff")
        self.levs_per_var_text = pn.widgets.StaticText(
            name="Your levels per variable -file", value=self.levs_per_var_file, background="#ffffff"
        )

    def view(self):

        about = pn.Column(
            self.text1,
            self.text2,
            self.text3,
            self.text4,
            self.text5,
            self.poi_text,
            self.levs_per_var_text,
            name="About",
        )

        return about
