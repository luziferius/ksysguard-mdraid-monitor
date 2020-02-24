# -*- coding: utf-8 -*-

"""setup.py: setuptools control."""


import re
from setuptools import setup, find_packages

project_name = "ksysguard_mdraid_monitor"
script_file = "{project_name}/{project_name}.py".format(project_name=project_name)
description = "Provides a KSysGuard backend to monitor Linux MDRAID software raid status"

with open(script_file, "r", encoding="utf-8") as opened_script_file:
    version = re.search(
        r"""^__version__\s*=\s*"(.*)"\s*""",
        opened_script_file.read(),
        re.M
        ).group(1)


with open("README.rst", "r", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name=project_name,
    packages=find_packages(),
    # add required packages to install_requires list
    # install_requires=["package", "package2"],
    entry_points={
        "console_scripts": [
            "{project_name} = {project_name}.{project_name}:main".format(project_name=project_name)
        ]
    },
    version=version,
    description=description,
    long_description=long_description,
    author="Thomas Hess",
    author_email="thomas.hess@udo.edu",
    url="",
    license="GPLv3+",
    # list of classifiers: https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Desktop Environment :: K Desktop Environment (KDE)',
        'Topic :: System :: Monitoring',
        'Environment :: No Input/Output (Daemon)',

    ],
)
