#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name='arpy',
		version='0.2.0',
		description='Library for accessing "ar" files',
		author=u'Stanisław Pitucha',
		author_email='viraptor@gmail.com',
		url='http://bitbucket.org/viraptor/arpy',
		py_modules=['arpy'],
		license="Simplified BSD",
		long_description="""'arpy' is a library for accessing the archive files and reading the contents. It supports extended long filenames in both GNU and BSD format. Right now it does not support the symbol tables.

Usage instructions are included in the module docstring. No fancy features were used, so it should work on any reasonable version of python 2.""",
		)

