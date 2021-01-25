#!/usr/bin/env python

from setuptools import setup

setup(
    name="transpose",
    version="0.0.2",
    description="Convert columns to rows and rows to columns",
    author="Adam Hooper",
    author_email="adam@adamhooper.com",
    url="https://github.com/CJWorkbench/transpose",
    packages=[""],
    py_modules=["transpose"],
    install_requires=["pandas~=0.25.2", "cjwmodule>=3.1.0"],
)
