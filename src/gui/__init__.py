import os
from pathlib import Path

__version__ = '1.0.0'

# Static path definitions within this direcectory (won't work as an installed package. Need to figure this out...)
this_path = Path(os.path.split(os.path.realpath(__file__))[0])
gui_path = this_path
