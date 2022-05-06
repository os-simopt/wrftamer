import os
import wrftamer
from wrftamer.gui.gui_base import gui_base
import panel as pn


class about_tab(gui_base):
    """
    Manual tests of gui sucessful (WRFTamer Version 1.1)
    """

    def __init__(self):
        super(about_tab, self).__init__()

        # Try to read poi file from file selector
        try:
            poi_file = os.environ["WRFTAMER_DEFAULT_POI_FILE"]
        except KeyError:
            poi_file = None

        message = f"This is wrftamer, Version {wrftamer.__version__}"

        self.text1 = pn.widgets.StaticText(
            name="Information", value=message, background="#ffffff"
        )
        self.text2 = pn.widgets.StaticText(
            name="Your Tamer Path", value=self.db_path, background="#ffffff"
        )
        self.text3 = pn.widgets.StaticText(
            name="Your run directory", value=self.run_path, background="#ffffff"
        )
        self.text4 = pn.widgets.StaticText(
            name="Your archive directory", value=self.archive_path, background="#ffffff"
        )
        self.text5 = pn.widgets.StaticText(
            name="Your plot directory", value=self.plot_path, background="#ffffff"
        )
        self.poi_text = pn.widgets.StaticText(
            name="Your poi file", value=poi_file, background="#ffffff"
        )

        self.poi_input = pn.widgets.FileInput(
            name="Select poi file", accept=".csv", multiple=False
        )

        @pn.depends(self.poi_input.param.filename, watch=True)
        def _update_text6(selection):
            if self.poi_input.filename is None:
                try:
                    self.poi_text.value = os.environ["WRFTAMER_DEFAULT_POI_FILE"]
                except KeyError:
                    self.poi_text.value = None
            else:
                self.poi_text.value = self.poi_input.filename

    def view(self):

        about = pn.Column(
            self.text1,
            self.text2,
            self.text3,
            self.text4,
            self.text5,
            self.poi_text,
            self.poi_input,
            name="About",
        )

        return about
