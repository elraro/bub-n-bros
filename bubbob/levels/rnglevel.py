from random import *
from math import *

import boarddef
from boarddef import LNasty, LMonky, LGhosty, LFlappy
from boarddef import LSpringy, LOrcy, LGramy, LBlitzy
from boarddef import RNasty, RMonky, RGhosty, RFlappy
from boarddef import RSpringy, ROrcy, RGramy, RBlitzy

def flat(mean,var):
    return randrange(mean-var,mean+var+1)

def dice(n,sides,orig=1):
    result = 0
    for i in range(n):
        result += orig+randrange(sides)
    return result

def fish(mu):
    def fact(n):
        r = 1.
        for i in range(1,n+1):
            r *= i
            pass
        return r
    scale = fact(0)/exp(-mu)
    dens = []
    while 1:
        x = len(dens)
        dens.append(int(scale*exp(-mu)*pow(mu,x)/fact(x)+0.5))
        if x > mu and dens[-1] == 0:
            break
        pass
    table = []
    x = 0
    for d in dens:
        for i in range(d):
            table.append(x)
            pass
        x += 1
        pass
    return choice(table)


class RandomLevel(boarddef.Level):
    WIDTH  = 32
    HEIGHT = 28
    MAXTRY = 1000
    # parameters of the 'mess generator'
    # mess_prob : the probability that a cell turn into a wall

    def __init__(self,num):
        try:
            self.__class__.walls
            #print 'Reusing previously generated level'
            #print self.__class__.walls
	    self.walls = self.__class__.walls
            boarddef.Level.__init__(self,num)
            return
        except AttributeError:
            pass

        #print 'Generating a new level'

        # map for the walls
        self.wmap = [ [' ' for x in range(self.WIDTH)] for y in range(self.HEIGHT) ]
        # map of the free cells
        self.fmap = [ [1 for x in range(self.WIDTH)] for y in range(self.HEIGHT) ]

        try:
            self.auto
        except AttributeError:
            pass
        else:
            self.generate()
            self.do_bonuses()

        for gw in self.genwalls:
            gw[0](self,*gw[1:])

        try:
            self.mlist
        except AttributeError:
            pass
        else:
            self.do_monsters()
        
        self.do_walls()
	self.walls = self.__class__.walls
        #print self.walls
        boarddef.Level.__init__(self,num)
        pass

    def setw(self,x,y,c='#'):
        if x > self.WIDTH-1 or x < 0 or y > self.HEIGHT-1 or y < 0:
            return
        if self.fmap[y][x]:
            self.wmap[y][x] = c
            self.fmap[y][x] = 0
            pass
        pass

    def clrw(self,x,y):
        if x > self.WIDTH-1 or x < 0 or y > self.HEIGHT-1 or y < 0:
            return
        self.wmap[y][x] = ' '
        self.fmap[y][x] = 1
        pass

    def mess(self, threshold):
        """Random fill of the board with walls.
        Only one argument, the probability that
        a cell turns out to be a wall.
        """
        for x in range(self.WIDTH):
            for y in range(self.HEIGHT):
                if random() < threshold:
                    self.setw(x,y)
                    pass
                pass
            pass
        pass

    def platforms(self, (nplat, space), (rng_holes, rng_width), full=1):
        """Place random platforms.
        args is a tuple with the following fields:
        0: a tuple containing the number of platforms and
           the minum space between two platforms,
        1: a tuple indicating in order:
           - the rng for the number of holes per platform
           - the rng for the width of the holes,
        2: a flag indicating whether the platform should cross
           the whole level or not.
        """
        plat = []
        for i in range(nplat):
            ntry = 100
            while ntry:
                y = randint(0,self.HEIGHT-1)
                found = 0
                for old in plat:
                    if abs(old-y) <= space:
                        found = 1
                        break
                    pass
                if not found:
                    plat.append(y)
                    break
                ntry -= 1
                pass
            if not ntry:
                continue  # ignore platform
            if full:
                x = 0
                w = self.WIDTH
            else:
                x = randint(0,self.WIDTH-1)
                w = randint(0,self.WIDTH-1)
                s = choice([-1,1])
		if s == -1:
                    w = min(w,x)
		    x -= w
		else:
                    w = min(w,self.WIDTH-x)
                pass
            for x in range(x,x+w):
                self.setw(x,y)
                pass
            for i in range(rng_holes()):
                hx = randint(x,x+w)
                hw = rng_width()
                for h in range(hx-hw/2,hx+hw/2):
                    self.clrw(h,y)
                    pass
                pass
            pass
        pass

    def lines(self, rng_len, nlines, rng_angle=None):
        """Generate a set of lines in any direction. It takes three
        arguments, a rng for the length the lines, the number of lines,
        and a rng for the angle.
        """
        if rng_angle is None:
            rng_angle = lambda : choice([0]+[pi/i for i in range(3,21)]+[-pi/i for i in range(3,21)])
        for i in range(nlines):
            len = rng_len()
            angle = rng_angle()
            ntry = self.MAXTRY
            while ntry:
                sx = randint(0,self.WIDTH-1)
                sy = randint(0,self.HEIGHT-1)
                dx = int(sx + len*cos(angle) + 0.5)
                dy = int(sy + len*sin(angle) + 0.5)
                if dx < self.WIDTH and dy < self.HEIGHT and dx >= 0 and dy >= 0:
                    break
                ntry -= 1
                pass
            if ntry == 0:
                break
            if abs(dx-sx) > abs(dy-sy):
                for x in range(dx-sx+1):
                    y = (2*(dy-sy)*x/(dx-sx)+1)/2
                    self.setw(sx+x,sy+y)
                    pass
                pass
            else:
                for y in range(dy-sy+1):
                    x = (2*(dx-sx)*y/(dy-sy)+1)/2
                    self.setw(sx+x,sy+y)
                    pass
                pass
            pass
        pass

    def rooms(self, rng_radius, rng_e, n_rooms):
        """Generate rooms. It takes the following arguments:
        0: the rng for the radius of the room
        1: the rng for the excentricity of the room
        2: the number of rooms
        """
        for i in range(n_rooms):
            cx = randint(0,self.WIDTH-1)
            cy = randint(0,self.HEIGHT-1)
            r = rng_radius()
            e = rng_e()*1.0
            left   = cx-int(r*e+0.5)
            right  = cx+int(r*e+0.5)
            top    = cy-int(r/e+0.5)
            bottom = cy+int(r/e+0.5)
            for x in range(left,right+1):
                self.setw(x,top)
                self.setw(x,bottom)
                pass
            for y in range(top,bottom+1):
                self.setw(left,y)
                self.setw(right,y)
                pass
            for x in range(left+1,right):
                for y in range(top+1,bottom):
                    if x > 0 and x < self.WIDTH-1 and y > 0 and y < self.HEIGHT-1:
                        self.fmap[y][x] = 0
                    pass
                pass
            pass
        pass

    def holes(self, rng_radius, rng_e, n_holes, rng_rect):
        """Generate a set of holes in the level. It takes four args:
        0: the rng for the radius of the holes
        1: the rng for the excentricity of the holes
        2: the number of holes
        3: the rng for the shape of the hole 0 for circular, 1 for rectangular
        """
        for i in range(n_holes):
            cx = randint(0,self.WIDTH-1)
            cy = randint(0,self.HEIGHT-1)
            r = rng_radius()
            e = rng_e()*1.0
            rect = rng_rect()
            for x in range(cx-int(r*e+0.5),cx+int(r*e+0.5)+1):
                for y in range(cy-int(r/e+0.5),cy+int(r/e+0.5)+1):
                    if not rect and (((x-cx)/e)**2+((y-cy)*e)**2) > r**2:
                        continue
                    self.clrw(x,y)
                    pass
                pass
            pass
        pass

    def close(self):
        "Just close the level with floor and roof"
        for x in range(self.WIDTH):
            self.setw(x,0) 
            self.setw(x,self.HEIGHT)
        pass

    def do_monsters(self):
        """Create monsters based on the requested settings.
        mlist is a list of monster setting. Each item is a tuple with:
        0: the list of monster to uses (each item might be a tuple)
        1: the rng for the number of monsters to pick in the list.
        """
        from string import ascii_letters
        current = 'a'
        for ms in self.mlist:
            n_monsters = ms[1]()
            for idx in range(n_monsters):
                self.__class__.__dict__[current] = choice(ms[0])
                ntry = self.MAXTRY
                while ntry:
                    x = randint(0,self.WIDTH-2)
                    y = randint(0,self.HEIGHT-1)

                    if self.wmap[y][x] == self.wmap[y][x+1] == ' ':
                        self.wmap[y][x] = current
                        break
                    ntry -= 1
                    pass
                current = chr(ord(current)+1)
                pass
            pass
        pass

    def do_walls(self):
        "Build the actual walls map for the game."
        self.__class__.walls = ''
        for y in range(self.HEIGHT-1):
            self.__class__.walls += '##'
            for x in range(self.WIDTH):
                self.__class__.walls += self.wmap[y][x]
                pass
            self.__class__.walls += '##\n'
            pass
        self.__class__.walls += '##'
        for x in range(self.WIDTH):
            if self.wmap[0][x] == '#' or self.wmap[self.HEIGHT-1][x] == '#':
                self.__class__.walls += '#'
            else:
                self.__class__.walls += ' '
            pass
        self.__class__.walls += '##\n'
        pass

    def do_bonuses(self):
        self.__class__.letter    = choice([0,1])
        self.__class__.fire      = choice([0,1])
        self.__class__.lightning = choice([0,1])
        self.__class__.water     = choice([0,1])
        self.__class__.top       = choice([0,1])
        pass

    def generate(self):
        "Generate random level settings."
        self.mlist = [([
            LNasty, LMonky, LGhosty, LFlappy, LSpringy, LOrcy, LGramy, LBlitzy,
            RNasty, RMonky, RGhosty, RFlappy, RSpringy, ROrcy, RGramy, RBlitzy,
            ],lambda : flat(12,4))]
        gens = choice([16,16,16,16,16,16,20,20,8,8,8,8,4,4,4,4,2,2,2,2,1,1,3,5,6,7])
        self.genwalls = []
        if gens & 16:
            # generate rooms
            print 'Using the romms generator'
            nr = choice([1,2,2,2,3,3,4,5])
            self.genwalls.append((RandomLevel.rooms,
                                  lambda : flat(9-nr,2),    # the half size of the room
                                  lambda : uniform(0.8,1.2), # the excentricity of the room
                                  nr))                       # the number of rooms
        if gens & 8:
            # generate a holes generator
            # as this is interesting only if the level is filled somehow
            print 'Using the holes generator'
            self.genwalls.append((RandomLevel.mess,1-uniform(0.2,0.5)))
            nh = choice([1,1,2,2,2,3,3,3,4,5])
            self.genwalls.append((RandomLevel.holes,
                                  lambda : flat(9-nh,2),       # radius of the holes
                                  lambda : uniform(0.9,1.1),   # excentricity
                                  nh,                          # number of holes
                                  lambda : choice([0,0,0,1]))) # circle or rectangle
        if gens & 4:
            # generate a lines generator
            print 'Using the lines generator'
            self.genwalls.append((RandomLevel.lines,
                                  lambda : dice(7,3), # line length
                                  dice(2,3)))         # number of lines
        if gens & 2:
            # generate a platforms generator
            print 'Using the platforms generator'
            nplat  = dice(2,4,0)
            if nplat: space  = flat((self.HEIGHT-1)/nplat/2,(self.HEIGHT-1)/nplat/2-1)
            else:     space = 1
            nholes = lambda : dice(1,3,0)          
            wholes = lambda : dice(2,3)
            full = randrange(2)
            self.genwalls.append((RandomLevel.platforms,
                                  (nplat,space),   # number of platform and spacing
                                  (nholes,wholes), # number of holes and width
                                  full))           # full width platform
            pass
        if gens & 1:
            # generate a mess generator
            print 'Using the mess generator'
            if gens & ~2:
                offset = 0
                scale = 0.05
            else:
                offset = 0.05
                scale = 0.10
                pass
            self.genwalls.append((RandomLevel.mess,offset+random()*scale))
            pass
        if random() < 0.2:
            self.genwalls.append((RandomLevel.close,))
        pass


Levels = []
for i in range(25):
    class level(RandomLevel):
	auto = 1
    Levels.append(level)

class levelfinal(RandomLevel):
    genwalls = [(RandomLevel.platforms,(4,3),(lambda:flat(1,1),lambda:flat(4,2)),1)]
Levels.append(levelfinal)
