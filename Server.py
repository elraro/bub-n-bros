#! /usr/bin/env python

#
#  This script is used to start the server.
#  Use with '--help' for more information.
#
#  It is actually just a wrapper around bubbob/bb.py.
#

import sys, os

if __name__ == '__main__':
    LOCALDIR = sys.argv[0]
else:
    LOCALDIR = __file__
LOCALDIR = os.path.abspath(os.path.dirname(LOCALDIR))
sys.path.append(os.path.abspath(os.path.join(LOCALDIR, 'bubbob')))

import bb
bb.main()
