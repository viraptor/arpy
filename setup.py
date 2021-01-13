#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='arpy',
		version='2.2.0',
		description='Library for accessing "ar" files',
		author='Stanisław Pitucha',
		author_email='viraptor@gmail.com',
		url='https://github.com/viraptor/arpy',
		py_modules=['arpy'],
		license="Simplified BSD",
		test_suite='test',
		long_description="""'arpy' is a library for accessing the archive files and reading the contents. It supports extended long filenames in both GNU and BSD format. Right now it does not support the symbol tables, but can ignore them gracefully.

Usage instructions are included in the module docstring. Works with python >=3.5, as well as pypy3. (for python 2.x see versions 1.*)""",
		classifiers=[
			"Development Status :: 5 - Production/Stable",
			"License :: OSI Approved :: BSD License",
			"Programming Language :: Python :: 3.5",
			"Programming Language :: Python :: 3.6",
			"Programming Language :: Python :: 3.7",
			"Programming Language :: Python :: 3.8",
			"Programming Language :: Python :: Implementation :: PyPy",
			"Programming Language :: Python :: Implementation :: CPython",
			"Topic :: System :: Archiving",
			]
		)

