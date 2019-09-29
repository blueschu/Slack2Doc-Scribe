#!/usr/bin/env python3
import os

from setuptools import find_packages, setup

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, 'requirements.txt')) as requirements:
    REQUIREMENTS = requirements.read().splitlines()

with open(os.path.join(BASE_DIR, 'README.rst')) as readme:
    README = readme.read()

setup(
    name='Slack2Doc Scribe',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    description="A simple Flask app to log Slack messages to a Google Docs "
                "document for permanent and accessible storage.",
    long_description=README,
    zip_safe=False,
    install_requires=['Flask']
)
