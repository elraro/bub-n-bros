import os, sys

levels, ext = os.path.splitext(os.path.basename(sys.argv[1]))
sys.argv[1] = 'levels/%s.bin' % levels

execfile('bb.py')
