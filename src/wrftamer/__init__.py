import os
from pathlib import Path
from config_tools.config_tools import get_config

# Static path definitions within this direcectory (won't work as an installed package. Need to figure this out...)
this_path = Path(os.path.split(os.path.realpath(__file__))[0])
test_res_path = this_path / '../../tests/resources'
res_path = this_path / '../../resources'

assert test_res_path.is_dir()
assert res_path.is_dir()

# get package configuration

if os.environ.get('wrftamer_test_mode', 'False') == 'True':
    os.environ['wrftamer_config'] = str(test_res_path / 'test_config.yaml')

try:
    cfg = get_config(special_config=os.environ['wrftamer_config'])
except KeyError:
    print('environment varialbe wrftamer_config not found. Defaulting to a directory relative to $HOME')
    cfg = get_config(path_seed=this_path / '__init__.py')
