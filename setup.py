#!/usr/bin/env python3
from setuptools import setup

pyscripts = [
    'wt',
    'wt_gui'
]

scripts = (['scripts/' + s for s in pyscripts])

with open('README.md') as f:
    long_description = f.read()

exec(open('wrftamer/version.py').read())

setup(
    name='wrftamer',
    version=__version__,
    license="MIT",
    description='Management of WRF Projects and Experiments',
    long_description=long_description,
    url='https://github.com/os-simopt/WRFtamer.git',
    maintainer='Daniel Leukauf',
    maintainer_email='daniel.leukauf@zsw-bw.de',
    scripts=scripts,
    packages=['wrftamer'],
    package_data={'wrftamer': ['resources/*.csv', 'resources/*.yaml', 'resources/namelist*']},
    zip_safe=False)
