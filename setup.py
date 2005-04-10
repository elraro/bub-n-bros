#!/usr/bin/env python
"""
setup.py - script for building MyApplication

Usage:
    % python setup.py py2app
"""
from distutils.core import setup
import py2app

# Note that you must replace hypens '-' with underscores '_'
# when converting option names from the command line to a script.
# For example, the --argv-emulation option is passed as 
# argv_emulation in an options dict.
py2app_options = dict(
    # Map "open document" events to sys.argv.
    # Scripts that expect files as command line arguments
    # can be trivially used as "droplets" using this option.
    # Without this option, sys.argv should not be used at all
    # as it will contain only Mac OS X specific stuff.
    argv_emulation=True,

    # Required to gain access to pygame.
    includes='pygame',

    # This is a shortcut that will place MyApplication.icns
    # in the Contents/Resources folder of the application bundle,
    # and make sure the CFBundleIcon plist key is set appropriately.
    iconfile='BubBob.icns',

    # The java directory is not included because py2app crashes with it.
    resources='LICENSE.txt,bubbob,common,display,http2,metaserver',

    # Bub-n-bros Bundle data.
    plist= dict(
        CFBundleIdentifier='net.sourceforge.bub-n-bros',
        CFBundleVersion='1.3.+',
        CFBundleName='Bub-n-Bros',
    )
)

setup(
    app=['BubBob.py'],
    options=dict(
        # Each command is allowed to have its own
        # options, so we must specify that these
        # options are py2app specific.
        py2app=py2app_options
    )
)

# At that point we have a bundles that include pygame but py2app
# doesn't set PYTHONPATH correctly until we add it as a package.
# This done in a second step because py2app crashes if it's combined
# with the previous one.

py2app_options['packages'] = 'pygame'

setup(
    app=['BubBob.py'],
    options=dict(
        # Each command is allowed to have its own
        # options, so we must specify that these
        # options are py2app specific.
        py2app=py2app_options
    )
)
