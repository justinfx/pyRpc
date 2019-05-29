#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sys import version_info

try:
    from setuptools import setup, find_packages
except ImportError:
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup, find_packages

ctx = {}

if version_info[0] < 3:
    execfile('pyRpc/_version.py', {}, ctx)
else:
    exec(compile(open('pyRpc/_version.py', "rb").read(), 'pyRpc/_version.py', 'exec'), {}, ctx)

setup(
    name = "pyRpc",
    version = ctx['__version__'],
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Communications',
    ]
)
