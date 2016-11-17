# -*- coding: utf8 -*-

# Low-resource message queue framework
# Setup metadata file
# Copyright (c) 2016 Roman Kharin <romiq.kh@gmail.com>


import os
import setuptools

module_path = os.path.join(os.path.dirname(__file__), "lrmq", "__init__.py")
version_line = [line for line in open(module_path)
    if line.startswith("__version__")][0]
__version__ = version_line.split('__version__ = ')[-1][1:][:-2]

setuptools.setup(name = "lrmq",
    version = __version__,
    description = "Low-resource message queue framework",
    long_description = open("README.rst").read(),
    #url="http://github.com/RomanKharin/lrmq",
    author = "Roman Kharin",
    author_email = "romiq.kh@gmail.com",
    license = "MIT",
    packages = ["lrmq", "lrmq.client"],
    zip_safe = False,
      
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        ]
    )

