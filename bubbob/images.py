from __future__ import generators
import gamesrv, os
from sprmap import sprmap
from patmap import patmap

KEYCOL = 0x010101

ActiveSprites = []
SpritesByLoc = {}


class ActiveSprite(gamesrv.Sprite):
    touchable = 0
    imgsetter = None
    angry = 0
    priority = 0
    
    def __init__(self, *args):
        gamesrv.Sprite.__init__(self, *args)
        if self.priority:
            ActiveSprites.insert(0, self)
        else:
            ActiveSprites.append(self)
        self.ranges = []
        self.gen = []
    def action(self):
        i = self.angry
        genlist = self.gen[:]
        while 1:
            if not self.alive:
                return
            try:
                while genlist:
                    gen = genlist.pop(0)
                    gen.next()
                    if not self.alive:
                        return
            except StopIteration:
                try:
                    self.gen.remove(gen)
                except ValueError:
                    pass
                continue
            if not i:
                break
            i = 0
            genlist = self.gen[:]
        # record position
        if self.touchable:
            x = int(self.x) &~ 7
            y = int(self.y) &~ 7
            if self.touchable != (x, y):
                self.touchable = x, y
                for key in self.ranges:
                    del key[self]
                del self.ranges[:]
                xrange = range(x>>5, (x+self.ico.w+38)>>5)
                for y in range(y>>4, (y+self.ico.h+22)>>4):
                    for x in xrange:
                        key = SpritesByLoc.setdefault((x,y), {})
                        key[self] = 1
                        self.ranges.append(key)
    def kill(self):
        self.untouchable()
        del self.gen[:]
        ActiveSprites.remove(self)
        gamesrv.Sprite.kill(self)

    def untouchable(self):
        self.touchable = 0
        for key in self.ranges:
            del key[self]
        del self.ranges[:]

    def play(self, snd, volume=0.8):
        import boards
        xmin = 2*boards.CELL
        xmax = boards.bwidth-4*boards.CELL
        snd.play(volume, pad=float(self.x-xmin)/(xmax-xmin))

    def setimages(self, gen):
        if self.imgsetter is not None:
            try:
                self.gen.remove(self.imgsetter)
            except ValueError:
                pass
        self.imgsetter = gen
        if gen is not None:
            self.gen.append(gen)

    # common generators
    def cyclic(self, nimages, speed=5):
        images = [sprget(n) for n in nimages]
        while 1:
            for img in images:
                self.seticon(img)
                for i in range(speed):
                    yield None

    def imgseq(self, nimages, speed=5, repeat=1):
        images = [sprget(n) for n in nimages]
        for r in range(repeat):
            for img in images:
                self.seticon(img)
                for i in range(speed):
                    yield None

    def die(self, nimages, speed=1):
        for n in nimages:
            self.seticon(sprget(n))
            for i in range(speed):
                yield None
        self.kill()

    def parabolic(self, dxy):
        import boards
        from boards import CELL
        nx = self.x
        ny = self.y
        dx, dy = dxy
        while ny < boards.bheight:
            nx += dx
            ny += dy
            dy += 0.3
            if nx < 2*CELL:
                nx = 2*CELL
                dx = abs(dx)
            elif nx >= boards.bwidth - 4*CELL:
                nx = boards.bwidth - 4*CELL
                dx = -abs(dx)
            self.move(int(nx), int(ny))
            dxy[:] = [dx, dy]
            yield None

    def following(self, other, dx=0, dy=0):
        while other.alive:
            self.move(other.x + dx, other.y + dy)
            yield None
        self.kill()

    def touchdelay(self, delay):
        for i in range(delay):
            yield None
        self.touchable = 1

    def touching(self, margin=0):
        return touching(self.x, self.y, self.ico.w, self.ico.h, margin)


def touching(x1, y1, w1, h1, margin=0):
    touch = {}
    x1 = int(x1)
    y1 = int(y1)
    xrange = range(x1>>5, (x1+w1+31)>>5)
    for y in range(y1>>4, (y1+h1+15)>>4):
        for x in xrange:
            touch.update(SpritesByLoc.get((x,y), {}))
    return [s for s in touch
            if x1+margin < s.x+s.ico.w and y1+margin < s.y+s.ico.h and
               s.x+margin < x1+w1 and s.y+margin < y1+h1]


def sprget(n):
    filename, rect = sprmap[n]
    filename = os.path.join('images', filename)
    return gamesrv.getbitmap(filename, KEYCOL).geticon(*rect)

def haspat(n):
    return n in patmap

def patget(n, keycol=None):
    filename, rect = patmap[n]
    filename = os.path.join('tmp', filename)
    return gamesrv.getbitmap(filename, keycol).geticon(*rect)

extramap = {
    'shield-left':  ('extra1.ppm', (0, 0, 32, 32)),
    'shield-right': ('extra1.ppm', (0, 32, 32, 32)),
    'questionmark3':('extra2.ppm', (0, 0, 16, 16)),
    'questionmark1':('extra2.ppm', (0, 16, 16, 16)),
    'questionmark5':('extra2.ppm', (0, 32, 16, 16)),
    'questionmark2':('extra2.ppm', (0, 48, 16, 16)),
    'questionmark4':('extra2.ppm', (0, 64, 16, 16)),
    'percent':      ('extra2.ppm', (0, 80, 16, 16)),
    'colon':        ('extra2.ppm', (0, 96, 16, 16)),
    ('eyes', 0,0):  ('extra3.ppm', (0, 0, 32, 32)),
    ('eyes', 0,-1): ('extra3.ppm', (0, 32, 32, 32)),
    ('eyes', -1,0): ('extra3.ppm', (0, 64, 32, 32)),
    ('eyes', -1,-1):('extra3.ppm', (0, 96, 32, 32)),
    ('eyes', 1,0):  ('extra3.ppm', (0, 128, 32, 32)),
    ('eyes', 1,-1): ('extra3.ppm', (0, 160, 32, 32)),
    'eyes-blink':   ('extra3.ppm', (0, 192, 32, 32)),
##    ('smstar','blue'   ,0): ('extra4.ppm', ( 0,  0, 16, 16)),
##    ('smstar','blue'   ,1): ('extra4.ppm', ( 0, 16, 16, 16)),
##    ('smstar','yellow' ,0): ('extra4.ppm', ( 0, 32, 16, 16)),
##    ('smstar','yellow' ,1): ('extra4.ppm', ( 0, 48, 16, 16)),
##    ('smstar','red'    ,0): ('extra4.ppm', (16,  0, 16, 16)),
##    ('smstar','red'    ,1): ('extra4.ppm', (16, 16, 16, 16)),
##    ('smstar','green'  ,0): ('extra4.ppm', (16, 32, 16, 16)),
##    ('smstar','green'  ,1): ('extra4.ppm', (16, 48, 16, 16)),
##    ('smstar','magenta',0): ('extra4.ppm', (32,  0, 16, 16)),
##    ('smstar','magenta',1): ('extra4.ppm', (32, 16, 16, 16)),
##    ('smstar','cyan'   ,0): ('extra4.ppm', (32, 32, 16, 16)),
##    ('smstar','cyan'   ,1): ('extra4.ppm', (32, 48, 16, 16)),
    ('starbub','blue'   ,0): ('extra5.ppm', (0,  0, 32, 32)),
    ('starbub','blue'   ,1): ('extra5.ppm', (0, 32, 32, 32)),
    ('starbub','blue'   ,2): ('extra5.ppm', (0, 64, 32, 32)),
    ('starbub','yellow' ,0): ('extra5.ppm', (0, 96, 32, 32)),
    ('starbub','yellow' ,1): ('extra5.ppm', (0,128, 32, 32)),
    ('starbub','yellow' ,2): ('extra5.ppm', (0,160, 32, 32)),
    ('starbub','red'    ,0): ('extra5.ppm', (0,192, 32, 32)),
    ('starbub','red'    ,1): ('extra5.ppm', (0,224, 32, 32)),
    ('starbub','red'    ,2): ('extra5.ppm', (0,256, 32, 32)),
    ('starbub','green'  ,0): ('extra5.ppm', (0,288, 32, 32)),
    ('starbub','green'  ,1): ('extra5.ppm', (0,320, 32, 32)),
    ('starbub','green'  ,2): ('extra5.ppm', (0,352, 32, 32)),
    ('starbub','magenta',0): ('extra5.ppm', (0,384, 32, 32)),
    ('starbub','magenta',1): ('extra5.ppm', (0,416, 32, 32)),
    ('starbub','magenta',2): ('extra5.ppm', (0,448, 32, 32)),
    ('starbub','cyan'   ,0): ('extra5.ppm', (0,480, 32, 32)),
    ('starbub','cyan'   ,1): ('extra5.ppm', (0,512, 32, 32)),
    ('starbub','cyan'   ,2): ('extra5.ppm', (0,544, 32, 32)),
    'sheep-sm':     ('extra6.ppm', (0, 0, 32, 32)),
    'sheep-big':    ('extra6.ppm', (0, 32, 46, 50)),
    }
sprmap.update(extramap)

def getsample(fn, freq):
    return gamesrv.getsample(os.path.join('sounds', fn), freq)

SoundList = ['Pop', 'Jump', 'Die', 'LetsGo', 'Extralife',
             'Fruit', 'Extra', 'Yippee', 'Hurry', 'Hell', 'Shh']

class Snd:
    pass

def loadsounds(freqfactor=1):
    for key in SoundList:
        setattr(Snd, key, getsample(key.lower()+'.wav', freqfactor))

loadsounds()
music_intro  = gamesrv.getmusic('music/Snd1-8.wav')
music_game   = gamesrv.getmusic('music/Snd2-8.wav')
music_potion = gamesrv.getmusic('music/Snd3-8.wav')
music_modern = gamesrv.getmusic('music/Snd4-8.wav')
music_old    = gamesrv.getmusic('music/Snd5-8.wav')
music_game2  = gamesrv.getmusic('music/Snd6-8.wav')
#gamesrv.set_musics([music_intro, music_game], 1)
