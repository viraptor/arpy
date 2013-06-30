Arpy
====

This library can be used to access **ar** files from python. It's tested to work with python 2.6, 2.7, 3.3 and pypy. Travis status: [![Build Status](https://travis-ci.org/viraptor/arpy.png)](https://travis-ci.org/viraptor/arpy)

It supports both GNU and BSD formats and exposes the archived files using the standard python **file** interface.

Usage
=====

Standard file usage:
--------------------

    ar = arpy.Archive('file.ar'))
    ar.read_all_headers()
    
    # check all available files
    ar.archived_files.keys()
    
    # get the contents of the archived file
    ar.archived_files[b'some_file'].read()

Stream / pipe / ... usage:
--------------------------

    ar = arpy.Archive('file.ar'))
    for f in ar:
        print("got file name: %s" % f.header.name)
        print("with contents: %s" % f.read())

Contributions
=============

All contributions welcome. Just make sure that:

*  tests are provided
*  all current platforms are passing (tox configuration is provided)
*  coverage is close to 100% (currently only missing statements are those depending on python version being used)
