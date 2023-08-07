from wrftamer.wrftamer_paths import wrftamer_paths
import os


class path_base:
    def __init__(self):
        (
            self.home_path,
            self.db_path,
            self.run_path,
            self.archive_path,
            self.plot_path,
        ) = wrftamer_paths()

        # Try to read poi file from file selector
        try:
            self.poi_file = os.environ["WRFTAMER_DEFAULT_POI_FILE"]
        except KeyError:
            self.poi_file = None

        try:
            self.levs_per_var_file = os.environ["WRFTAMER_DEFAULT_LEVS_PER_VAR_FILE"]
        except KeyError:
            self.levs_per_var_file = os.path.split(os.path.realpath(__file__))[0] + \
                                     '/../resources/Levels_per_variable.yaml'
