#!/usr/bin/env python3
import sys
from setuptools import setup
import versioneer

SETUP_REQUIRES = ['setuptools >= 30.3.0']
# This enables setuptools to install wheel on-the-fly
SETUP_REQUIRES += ['wheel'] if 'bdist_wheel' in sys.argv else []

pyscripts = [
    'wt',
    'wt_gui',
    'run_ppp'
]

scripts = (['scripts/' + s for s in pyscripts])

setup(
    name='wrftamer',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    setup_requires=SETUP_REQUIRES,
    scripts=scripts,
    packages=['wrftamer', 'wrftamer.gui', 'wrftamer.plotting'],
    package_data={'wrftamer': ['resources/*.csv', 'resources/*.yaml', 'resources/namelist*']}
)
