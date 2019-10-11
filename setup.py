#!/usr/bin/env python3
import os

from setuptools import find_packages, setup

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, 'requirements.txt')) as requirements:
    REQUIREMENTS = requirements.read().splitlines()

with open(os.path.join(BASE_DIR, 'README.rst')) as readme:
    README = readme.read()

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Environment :: Web Environment',
    'Framework :: Flask',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

setup(
    name='slack2doc',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    description="A simple Flask app to log Slack messages to a Google Docs "
                "document for permanent and accessible storage.",
    long_description=README,
    url="https://github.com/gstrenge/Slack2Doc-Scribe",
    zip_safe=False,
    python_requires='~=3.6',
    install_requires=REQUIREMENTS,
)
