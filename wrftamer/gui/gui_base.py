from wrftamer.wrftamer_paths import wrftamer_paths


class gui_base:
    def __init__(self):
        (
            self.home_path,
            self.db_path,
            self.run_path,
            self.archive_path,
            self.plot_path,
        ) = wrftamer_paths()
