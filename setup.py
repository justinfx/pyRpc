#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages
    
import os


setup(
    name = "pyRpc",
    version = "0.1",
    url = 'https://github.com/justinfx/pyRpc',
    packages = find_packages(),
    include_package_data = True,
    install_requires = ['pyzmq'],
    author = "Justin Israel",
    author_email = "justinisrael@gmail.com",
    description = "A simple remote procedure call module using ZeroMQ",
    license = "BSD",
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Communications',
    ]
)