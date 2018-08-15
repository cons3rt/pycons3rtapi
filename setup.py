#!/usr/bin/env python

import os
import sys
from setuptools import setup, find_packages


py_version = sys.version_info[:2]


# Ensure supported python version
if py_version < (2, 7):
    raise RuntimeError('pycons3rtapi requires Python 2.7 or later')
elif py_version >= (3, 0):
    raise RuntimeError('pycons3rtapi does not support Python3 at this time')


here = os.path.abspath(os.path.dirname(__file__))


# Get the version
version_txt = os.path.join(here, 'pycons3rtapi/VERSION.txt')
version = open(version_txt).read().strip()


# Get the requirements
requirements_txt = os.path.join(here, 'cfg/requirements.txt')
requirements = []
with open(requirements_txt) as f:
    for line in f:
        requirements.append(line.strip())

dist = setup(
    name='pycons3rtapi',
    version=version,
    description='Python API for CONS3RT',
    long_description=open('README.md').read(),
    author='Joe Yennaco',
    author_email='joe.yennaco@jackpinetech.com',
    url='https://github.com/cons3rt/pycons3rtapi',
    include_package_data=True,
    license='GNU GPL v3',
    packages=find_packages(),
    zip_safe=True,
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'cons3rt = pycons3rtapi.cons3rt:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent'
    ]
)
