#
# This test generates 100 times 25 random levels and checks
# that it doesn't crash, and that it gives levels that are
# possible (in the limited sense of not having any full-
# column walls)
#

import sys
sys.path.append('..')
sys.path.append('../common')

for i in range(100):
    print '%4d:' % i,
    d = {'__name__': 'RandomLevels'}
    execfile('levels/RandomLevels.py', d)
    for i, Lvl in enumerate(d['Levels']):
        level = Lvl(i)
        for x in range(2, level.width-2):
            for y in range(0, level.height):
                if level.walls[y][x] == ' ':
                    break
            else:
                for line in level.walls:
                    print line
                raise AssertionError("full height wall in column %d" % x)
