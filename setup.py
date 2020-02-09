"""Projecttile package build script"""

import sys

from setuptools import setup, find_packages


open_kwds = {}
if sys.version_info > (3,):
    open_kwds["encoding"] = "utf-8"

with open("projecttile/__init__.py") as f:
    for line in f:
        if "__version__" in line:
            version = line.split("=")[1].strip().strip('"').strip("'")
            continue

with open("README.rst", **open_kwds) as f:
    readme = f.read()

setup(
    name="projecttile",
    version=version,
    description="WebMapTileService tile utilities",
    long_description=readme,
    classifiers=["Programming Language :: Python :: 3",],
    keywords="mapping, tiles",
    author="Huite Bootsma",
    author_email="huitebootsma@gmail.com",
    url="https://github.com/huite/projecttile",
    license="BSD",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
)
