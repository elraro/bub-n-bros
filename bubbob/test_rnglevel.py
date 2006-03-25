#
# This test generates 100 times 25 random levels and checks
# that it doesn't crash, and that it gives levels that are
# possible (in the limited sense of not having any full-
# column walls)
#
# this test accepts the following parameters:
# -wall    show the level layout
# -wind    show the level wind pattern
#

import sys
sys.path.append('..')
sys.path.append('../common')

n_lvls = 100
show_lvl = 0

for arg in sys.argv:
    if arg == '-wall':
        show_lvl |= 1
        n_lvls = 2
    if arg == '-wind':
        show_lvl |= 2
        n_lvls = 2

def printlvl(level):
    if show_lvl:
        print "\n\n"
        for y in range(level.HEIGHT):
            str = ""
            if show_lvl & 1:
                str = level.walls[y]
            if show_lvl & 2:
                if str:
                    str += " | "
                str += level.winds[y]
            print str

for i in range(n_lvls):
    print '%4d:' % i,
    d = {'__name__': 'RandomLevels'}
    execfile('levels/RandomLevels.py', d)
    for i, Lvl in enumerate(d['Levels']):
        level = Lvl(i)
        printlvl(level)
        for x in range(2, level.width-2):
            for y in range(0, level.height):
                if level.walls[y][x] == ' ':
                    break
            else:
                for line in level.walls:
                    print line
                raise AssertionError("full height wall in column %d" % x)
