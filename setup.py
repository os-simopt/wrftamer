#!/usr/bin/env python3
from setuptools import setup

pyscripts = [
    'wt',
    'wt_gui',
    'run_ppp'
]

scripts = (['scripts/' + s for s in pyscripts])

with open('README.md') as f:
    long_description = f.read()

exec(open('WRFtamer/version.py').read())

setup(
    name='WRFtamer',
    version=__version__,
    license='LICENCE.txt',
    description='A python packate to help you mangaging WRF projects and experiments',
    long_description=long_description,
    url='https://github.com/os-simopt/WRFtamer.git',
    maintainer='Daniel Leukauf',
    maintainer_email='daniel.leukauf@zsw-bw.de',
    scripts=scripts,
    packages=['WRFtamer', 'WRFtamer.gui', 'WRFtamer.plotting'],
    package_data={'WRFtamer': ['resources/*.csv', 'resources/*.yaml', 'resources/namelist*']}
)
