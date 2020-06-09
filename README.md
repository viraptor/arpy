Arpy
====

This library can be used to access **ar** files from python. It's tested to work with python 3.5+ and pypy3. (for earlier pythons see version <2) Travis status: [![Build Status](https://travis-ci.org/viraptor/arpy.png)](https://travis-ci.org/viraptor/arpy)

It supports both GNU and BSD formats and exposes the archived files using the standard python **file** interface.

Usage
=====

Standard file usage:
--------------------

With context managers:

    with arpy.Archive('file.ar') as ar:
        print("files: %s" % ar.namelist())
        with ar.open('content.txt') as f:
            print(f.read())

Via headers for duplicate names:

    with arpy.Archive('file.ar') as ar:
        for header in ar.infolist():
            print("file: %s" % header.name)
            with ar.open(header) as f:
                print(f.read())

Or directly:

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
