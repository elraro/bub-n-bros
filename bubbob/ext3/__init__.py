from __future__ import generators
import os, math, random
import images, gamesrv
from images import ActiveSprite
import boards
from boards import CELL, HALFCELL, bget
from mnstrmap import GreenAndBlue, Fire
from bonuses import Bonus
from player import Dragon, BubPlayer
import monsters, bubbles

LocalDir = os.path.basename(os.path.dirname(__file__))

localmap = {
    ('gala', 0) :  ('image1.ppm', ( 0,  0, 32, 32)),
    ('gala', 1) :  ('image1.ppm', ( 0, 32, 32, 32)),
    ('gala', 2) :  ('image1.ppm', ( 0, 64, 32, 32)),
    }

music = gamesrv.getmusic(os.path.join(LocalDir, 'music.wav'))
snd_shoot = gamesrv.getsample(os.path.join(LocalDir, 'shoot.wav'))


class GalagaDragon(Dragon):

    def firenow(self):
        self.fire = 1
##        self.dir = -self.dir
##        self.dcap['lookforward'] *= -1
##        self.gen.append(self.restorelook())
        ico = images.sprget(GreenAndBlue.new_bubbles[self.bubber.pn][0])
        s = Shot(ico, self.x, self.y)
        s.d = self
        s.gen = [s.straightup(self)]
        self.play(snd_shoot)

##    def restorelook(self):
##        for i in range(4):
##            yield None
##        self.dcap['lookforward'] *= -1
##        self.dir = -self.dir

    def galaga_setup(self):
        icons = [images.sprget(ico)
                 for ico in GreenAndBlue.comming[self.bubber.pn]]
        self.galaga_icons = ([icons[0]] * 4 +
                             [icons[1]] * 4 +
                             [icons[2]] * 4 +
                             [icons[1]] * 4)
        self.overlay_icons = [images.sprget(('gala', n)) for n in range(3)]
        self.overlay_sprite = ActiveSprite(self.overlay_icons[0], self.x, self.y)

    def dying(self, *args, **kw):
        del self.galaga_icons[:]
        dxy = [3*self.dir, -7]
        self.overlay_sprite.gen.append(self.overlay_sprite.parabolic(dxy))
        self.overlay_sprite = None
        for t in Dragon.dying(self, *args, **kw):
            yield t

    def seticon(self, ico):
        if self.galaga_icons:
            ico = self.galaga_icons.pop(0)
            self.galaga_icons.append(ico)
        Dragon.seticon(self, ico)

    def to_front(self):
        Dragon.to_front(self)
        if self.overlay_sprite:
            self.overlay_sprite.move(self.x, self.y,
                                     random.choice(self.overlay_icons))
            self.overlay_sprite.to_front()


class Shot(bubbles.Bubble):
    touchable = 0
    
    def straightup(self, dragon):
        ymin = -self.ico.h
        while self.y > ymin:
            self.step(0, -7)
            yield None
            self.step(0, -8)
            touching = images.touching(self.x+CELL-1, self.y+CELL-1, 2, 2)
            touching = [s for s in touching if isinstance(s, Alien)]
            if touching:
                self.startnormalbubble(dx=0, dy=0)
                random.choice(touching).in_bubble(self)
                dragon.galaga.scores[dragon.bubber] += 1
                return
            yield None


class Alien(monsters.Monster):
    ANGLES = 32
    SPEED = 5
    ANGLE_TABLE = [(SPEED * math.cos(a*2.0*math.pi/ANGLES),
                    -SPEED * math.sin(a*2.0*math.pi/ANGLES))
                   for a in range(ANGLES)]
    touchable = 0
    
    def __init__(self, galaga, squadron, rank, relativey):
        centerx = boards.bwidth // 2
        go_left = squadron % 2
        dx = (1,-1)[go_left]
        halfspan = centerx*7//12
        relativex = - halfspan + 4*CELL*rank
        if relativex > halfspan:
            raise StopIteration
        
        if squadron % 3 == 2:
            from mnstrmap import Ghosty as mcls
        else:
            from mnstrmap import Flappy as mcls
        mdef = mcls(centerx // CELL - 1, -7, go_left)
        mdef.left_weapon = mdef.right_weapon = [Fire.drop]
        monsters.Monster.__init__(self, mdef)

        self.path = [(None, centerx + (dx*centerx)*2//3, boards.bheight//3),
                     (None, centerx - (dx*centerx)*4//5, boards.bheight//6),
                     (galaga, -dx*relativex, -relativey)]
        self.gen = [self.waiting(rank * 20)]
        self.in_place = 0
        galaga.nbmonsters += 1

    def default_mode(self, angle=ANGLES//4):
        self.touchable = 1
        speed = self.SPEED
        relative, tx, ty = self.path[0]
        fx = self.x
        fy = self.y
        ymax = boards.bheight - 3*CELL
        cont = 1
        if relative:
            shoot_prob = 0.007
        else:
            shoot_prob = 0.025
        while cont:
            if self.angry:
                self.kill()   # never getting out of a bubble
                return
            if relative:
                dx = relative.globalx + tx
                dy = relative.globaly + ty
            else:
                dx = tx
                dy = ty
            dx -= self.x
            dy -= self.y
            
            tests = []
            for a1 in (-1, 0, 1):
                a1 = (angle+a1) % self.ANGLES
                testx, testy = self.ANGLE_TABLE[a1]
                testx -= dx
                testy -= dy
                tests.append((testx*testx+testy*testy, a1))
            ignored, angle = min(tests)
            if dx*dx+dy*dy > speed*speed:
                dx, dy = self.ANGLE_TABLE[angle]
            elif relative:
                self.in_place = 1
                if self.y > ymax and BubPlayer.DragonList:
                    for d in BubPlayer.DragonList:
                        d.gen = [d.dying(can_loose_letter=0)]
                    del BubPlayer.DragonList[:]
                    self.play(images.Snd.Die)
                    x0 = self.x//CELL + 1
                    if x0 < 2: x0 = 0
                    if x0 >= boards.width-2: x0 = boards.width-3
                    bubbles.FireFlame(x0, boards.height-2, None, [-1, 1],
                                      boards.width)
            else:
                self.path.pop(0)
                self.gen.append(self.default_mode(angle))
                cont = 0
            fx += dx
            fy += dy
            self.move(int(fx), int(fy))
            if dx and (self.dir > 0) != (dx > 0):
                self.dir = -self.dir
                self.resetimages()
            if random.random() < shoot_prob and self.y >= 0:
                monsters.DownShot(self)
            yield None

    def in_bubble(self, bubble):
        self.in_place = 2
        monsters.Monster.in_bubble(self, bubble)

    def argh(self, poplist=None, onplace=0):
        if poplist and poplist[0] is None:
            if self.alive:
                self.kill()
        else:
            monsters.Monster.argh(self, poplist, onplace)


class Galaga:
    
    def bgen(self):#, limittime = 30.1): # 0:30
        for t in boards.exit_board(0, music=[music]*99):
            yield t
        for t in curboard.clean_gen_state():
            yield t

        #tc = boards.TimeCounter(limittime)
        BubPlayer.FrameCounter += 99999   # end all bonus effects now
        self.scores = {}
        self.nbmonsters = 0
        finish = 0
        for t in self.frame():
            t = boards.normal_frame()
            self.build_dragons()
            yield t
            if len(BubPlayer.DragonList) == 0:
                finish += 1
                if finish == 20:
                    break
            else:
                finish = 0
            #tc.update(t)
            #if tc.time == 0.0:
            #    break

        #tc.restore()
        for t in boards.result_ranking(self.scores, self.nbmonsters):
            self.build_dragons()
            self.explode_bubbles()
            yield t

    def frame(self):
        y = curboard.height-1
        for x in range(2, curboard.width-2):
            if bget(x, y) == ' ':
                curboard.putwall(x, y)
        curboard.reorder_walls()
        for y in range(curboard.height-2, -1, -1):
            yield None
            yield None
            for x in range(2, curboard.width-2):
                if bget(x, y) == '#':
                    curboard.killwall(x, y)

        self.globalx = boards.bwidth // 2
        self.globaly = 0
        shifter = self.shifter()
        curboard.winds = [' ' * curboard.width] * curboard.height
        squadrons = len([p for p in BubPlayer.PlayerList if p.isplaying()])
        squadrons = 3 + (squadrons+1)//3
        nextsquad = 0
        relativey = 0
        squadtime = 0
        while 1:
            yield None
            if random.random() < 0.04:
                bubbles.sendbubble(bubbles.PlainBubble, top=0)
            in_place = {0: [], 1: [], 2: []}
            for s in BubPlayer.MonsterList:
                if isinstance(s, Alien):
                    in_place[s.in_place].append(s)
            toohigh = self.globaly - relativey < -3*CELL
            if in_place[1]:
                xbounds = [s.x for s in in_place[1]]
                self.alien_bounds = min(xbounds), max(xbounds)
                shifter.next()
            elif toohigh:
                self.globaly += 1
            squadtime -= 1
            if nextsquad >= squadrons:
                if not (in_place[0] or in_place[1]):
                    break
            elif squadtime < 0 and not toohigh:
                squadtime = 200
                try:
                    rank = 0
                    while 1:
                        Alien(self, nextsquad, rank, relativey)
                        rank += 1
                except StopIteration:
                    pass
                nextsquad += 1
                relativey += 4*CELL

    def shifter(self):
        while 1:
            # go right
            while self.alien_bounds[1] < boards.bwidth-5*CELL:
                self.globalx += 2
                yield None
            # go down
            for i in range(3*CELL):
                self.globaly += 1
                yield None
            # go left
            while self.alien_bounds[0] > 3*CELL:
                self.globalx -= 2
                yield None
            # go down
            for i in range(3*CELL):
                self.globaly += 1
                yield None

    def build_dragons(self):
        for p in BubPlayer.PlayerList:
            dragons = [d for d in p.dragons if not isinstance(d, GalagaDragon)]
            if (dragons and len(p.dragons) == len(dragons) and
                p not in self.scores):
                realdragons = [d for d in dragons if d.__class__ == Dragon]
                if realdragons:
                    dragon = random.choice(realdragons)
                    self.scores[p] = 0
                    dragon.__class__ = GalagaDragon
                    dragon.galaga_setup()
                    dragon.galaga = self
                    dragons.remove(dragon)
                    p.emotic(dragon, 4)
            for d in dragons:
                d.kill()

    def explode_bubbles(self):
        if BubPlayer.DragonList:
            for s in images.ActiveSprites:
                if isinstance(s, Shot) and s.touchable:
                    s.pop([None])
                    return


def run():
    global curboard
    from boards import curboard

    for key, (filename, rect) in localmap.items():
        filename = os.path.join(LocalDir, filename)
        images.sprmap[key] = (filename, rect)

    boards.replace_boardgen(Galaga().bgen())
