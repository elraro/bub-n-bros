from __future__ import generators
import random, math
import gamesrv
import images
import boards
from boards import *
from images import ActiveSprite
from mnstrmap import GreenAndBlue, LetterBubbles, Stars
from mnstrmap import Lightning, Water, Fire, SpinningBalls


bubble_wind = {
    '<': (-1, 0),
    '>': (+1, 0),
    '^': ( 0,-1),
    'v': ( 0,+1),
    'x': ( 0, 0),
    }


class Bubble(ActiveSprite):
    exploding_bubbles = range(131,136)
    red_bubbles       = [156, 157, 156, 155]
    white_bubbles     = [164, 165, 164, 163]
    pink_bubbles      = [172, 173, 172, 171]
    check_onbubble    = ([(0,-1)], [(0,1)])

    touchable = 1
    warp = 0
    default_windless = None
    catch_dragons = None
    nimages = GreenAndBlue.normal_bubbles

    def touched(self, dragon):
        o = []
        if abs(self.x - dragon.x) >= 25:
            if self.x < dragon.x:
                o.append((1,0))
            else:
                o.append((-1,0))
        if abs(self.y - dragon.y) >= 25:
            if self.y < dragon.y:
                o.append((0,1))
            else:
                o.append((0,-1))
        if o:
            self.obstacle = o
        elif (self.catch_dragons and
              abs(self.x - dragon.x) < 15 and abs(self.y - dragon.y) < 15):
            if dragon not in self.catch_dragons:
                self.catch_dragons.append(dragon)
        else:
            self.pop(dragon.poplist)
        return o == self.check_onbubble[dragon.bottom_up()]

    def can_catch_dragons(self, author):
        self.catch_dragons = [author]
        self.gen.append(self.catching_dragons())

    def catching_dragons(self):
        yield None   # time to catch several dragons
        dragons = self.catch_dragons
        self.catch_dragons = None
        author = dragons.pop(0)
        if dragons:
            import bonuses
            imglist = [self.nimages[d.bubber.pn][i]
                       for d in dragons for i in [1,2,1,0]]
            self.setimages(self.cyclic(imglist))
            self.warp = 1
            caught = [bonus for d in dragons
                      for bonus in d.listcarrybonuses()
                      if isinstance(bonus, CatchNote)]
            random.shuffle(caught)
            if len(dragons) < 2:
                points = 250
            else:
                self.play(images.Snd.Extra)
                if len(dragons) == 2:
                    points = 10000
                elif len(dragons) == 3:
                    points = 30000
                else:
                    points = 70000
            caught.insert(0, CatchNote(points))
            for bonus in caught:
                author.carrybonus(bonus, 111)
                bonuses.points(self.x, self.y-HALFCELL, author, bonus.points)
            for d in dragons:
                d.become_bubblingeyes(self)

    def pop(self, poplist=None):
        if self.touchable:
            self.play(images.Snd.Pop)
            self.poplist = poplist
            self.untouchable()
            self.gen = [self.die(Bubble.exploding_bubbles)]
            if poplist:
                dragon = poplist[0]
                points = self.popped(dragon)
                if dragon:
                    dragon.bubber.givepoints(points)
                self.gen.append(self.poprec())
            return 1
        else:
            return 0

    def popped(self, dragon):
        return 10

    def poprec(self):
        yield None
        for s in self.touching(0):
            if isinstance(s, Bubble):
                s.pop(self.poplist)

    def normal_movements(self, dx=0, dy=-1, timeout=800):
        self.obstacle = []
        time = 0
        touchbubble = timeout = (timeout or 0) * 2
        while 1:
            del self.obstacle[:]
            yield None
            timeout -= 2
            if not timeout:
                self.setimages(self.bubble_red())
            if timeout > touchbubble:
                continue
            if timeout&2:
                for s in self.touching(13+(timeout&6)):
                    if isinstance(s, Bubble) and s is not self:
                        if (s.x-self.x)*dx > 0 or (s.y-self.y)*dy > 0:
                            touchbubble = timeout - (timeout&12) - 3
                            break
                if timeout > touchbubble:
                    continue
            if (dx,dy) not in self.obstacle:
                if dx==dy==0:
                    if len(self.obstacle)==1:
                        dx1, dy1 = self.obstacle[0]
                        self.step(-dx1, -dy1)
                else:
                    self.step(dx, dy)
                if self.y < -2*CELL or self.y >= boards.bheight:
                    if not self.warp:
                        self.poplist = None
                        self.kill()
                        return
                    if self.vertical_warp():
                        dx = -dx
                w = wget(self.x, self.y)
                if w != ' ':
                    dx, dy = bubble_wind[w]
                elif self.default_windless:
                    dx, dy = self.default_windless

    def bubble_red(self, speed=5):
        for n in self.imgseq(Bubble.white_bubbles, repeat=3):
            yield n
        for n in self.imgseq(Bubble.pink_bubbles, repeat=4):
            yield n
        for n in self.imgseq(Bubble.red_bubbles, repeat=4):
            yield n
        for n in self.imgseq([Bubble.pink_bubbles[0], Bubble.red_bubbles[0]],
                             speed=2, repeat=10):
            yield n
        self.pop()


class CatchNote:
    def __init__(self, points):
        self.points = points
    def endaction(self, dragon):
        pass


class DragonBubble(Bubble):
    touchable = 0

    def __init__(self, d, x, y, dir, special_bubble=None, angle=0):
        self.d = d
        pn = d.bubber.pn
        imglist1 = GreenAndBlue.new_bubbles[pn]
        imglist2 = GreenAndBlue.normal_bubbles[pn]
        if angle:
            asin, acos = math.sin(angle), math.cos(angle)
        else:
            asin, acos = 0, 1
        Bubble.__init__(self, images.sprget(imglist1[0]), x + 12*dir, y)
        self.setimages(self.imgseq(imglist1[1:] + imglist2[2:3], 4))
        self.gen.append(self.throw_bubble(dir*d.dcap['shootthrust'],
                                          special_bubble, (acos,asin)))

    def throw_bubble(self, hspeed, special_bubble=None, (acos,asin)=(1,0)):
        from monsters import Monster
        nx = self.x
        ny = self.y
        stop = 0
        withmonster = 0
        while abs(hspeed) >= 4.0:
            touched_monsters = [s for s in self.touching(9)
                                if isinstance(s, Monster)]
            if touched_monsters:
                random.choice(touched_monsters).in_bubble(self)
                withmonster = 1
                break
            if asin:
                (nx, ny), moebius = vertical_warp(nx + hspeed*acos, ny + hspeed*asin)
                if moebius:
                    acos = -acos
            else:
                nx += hspeed
            hspeed *= 0.965
            xc = int(nx-3.8)//CELL+1
            yc = (self.y+HALFCELL)//CELL
            if bget(xc,yc) == '#' == bget(xc, yc+1):
                stop += 1
            if stop <= 1:
                self.move(int(nx+0.5), int(ny+0.5))
            yield None

        self.warp = withmonster
        if not withmonster:
            from bonuses import Bonus, BonusMaker
            touched_bonuses = [s for s in self.touching(15)
                               if isinstance(s, Bonus) and s.bubblable]
            if touched_bonuses:
                random.choice(touched_bonuses).in_bubble(self)
                withmonster = 1
            else:
                touched_bonuses = [s for s in self.touching(7)
                                   if isinstance(s, BonusMaker)]
                if touched_bonuses:
                    bonusmaker = random.choice(touched_bonuses)
                    bonus = bonusmaker.build()
                    bonusmaker.kill()
                    if bonus:
                        bonus.in_bubble(self)
                        withmonster = 1
        if special_bubble:
            cls = globals()[special_bubble]
            if not withmonster:
                b = cls(self.d.bubber.pn)
                b.move(self.x, self.y)
                b.can_catch_dragons(self.d)
                self.kill()
                return
        self.touchable = 1
        self.gen.append(self.normal_movements(
                                timeout=self.d.dcap['bubbledelay']))
        imglist = GreenAndBlue.normal_bubbles[self.d.bubber.pn]
        self.setimages(self.cyclic([imglist[1],
                                    imglist[2],
                                    imglist[1],
                                    imglist[0]]))
        if not withmonster:
            self.can_catch_dragons(self.d)


class BubblingEyes(ActiveSprite):
    
    def __init__(self, bubber, saved_caps, bubble):
        ico = images.sprget(('eyes', 0, 0))
        ActiveSprite.__init__(self, ico, bubble.x, bubble.y)
        self.bubber = bubber
        self.saved_caps = saved_caps
        self.gen = [self.playing_bubble(bubble)]
        
    def playing_bubble(self, bubble):
        from player import Dragon
        timer = 0
        red = 0
        normalbub = bubble.imgsetter
        redblinker = bubble.cyclic([Bubble.pink_bubbles[0], Bubble.red_bubbles[0]], 2)
        bubber = self.bubber
        ndir = random.choice([-1, 1])
        prev_dx_dy = None
        while not hasattr(bubble, 'poplist'):
            dx = bubber.wannago(self.saved_caps)
            if dx:
                ndir = dx
            if bubber.key_jump:
                dy = -1
            else:
                dy = 0
            if bubber.key_fire:
                red += 1
                if red > 20:
                    d = Dragon(bubber, self.x, self.y, ndir, self.saved_caps)
                    bubble.pop([d])
                    d.kill()
                    break
                if bubble.imgsetter is not redblinker:
                    normalbub = bubble.imgsetter
                    bubble.setimages(redblinker)
            else:
                red = 0
                if bubble.imgsetter is redblinker:
                    bubble.setimages(normalbub)
            key = ('eyes', dx, dy)
            if timer < 50:
                if (timer % 9) < 3:
                    key = 'eyes-blink'
            elif random.random() < 0.1:
                key = 'eyes-blink'
            timer += 1
            if bubble.x <= 3*HALFCELL and dx < 0:
                dx = 0
            if bubble.x >= boards.bwidth - 7*HALFCELL and dx > 0:
                dx = 0
            nx = bubble.x + dx
            ny = bubble.y + dy
            if timer&1:
                nx += dx
            else:
                ny += dy
            (nx, ny), moebius = boards.vertical_warp(nx, ny)
            bubble.move(nx, ny)
            self.move(nx+dx, ny+dy, images.sprget(key))
            if moebius:
                self.saved_caps['left2right'] *= -1
            if dx == dy == 0:
                bubble.default_windless = prev_dx_dy
            else:
                prev_dx_dy = dx, dy
                bubble.default_windless = 0, 0
            yield None
        # jumping out of the bubble
        self.setimages(self.cyclic(GreenAndBlue.comming[bubber.pn], 2))
        dxy = [(random.random()-0.5) * 9.0,
               (random.random()+0.5) * (-5.0)]
        for n in self.parabolic(dxy, 1):
            yield n
            if dxy[1] >= 4.0:
                break
        if dxy[0] < 0:
            ndir = -1
        else:
            ndir = 1
        d = Dragon(bubber, self.x, self.y, ndir, self.saved_caps)
        d.dcap['shield'] = 50
        bubber.dragons.append(d)
        self.kill()

    def kill(self):
        try:
            self.bubber.dragons.remove(self)
        except ValueError:
            pass
        ActiveSprite.kill(self)


class BonusBubble(Bubble):
    max = None
    timeout = None

    def __init__(self, pn, nimages=None):
        if nimages is None:
            nimages = self.nimages[pn]
        b = boards.curboard
        if b.top == 0:
            testline = b.walls[-1]
            x, y = self.findhole(testline), boards.bheight
            dx, dy = 0, -1
        elif b.top == 1:
            testline = b.walls[0]
            x, y = self.findhole(testline), -2*CELL
            dx, dy = 0, 1
        elif b.top == 2:
            x, y = -2*CELL, random.randint(2*CELL, boards.bheight-4*CELL)
            dx, dy = 1, 0
        else:  # b.top == 3:
            x, y = (boards.bwidth - CELL,
                    random.randint(2*CELL, boards.bheight-4*CELL))
            dx, dy = -1, 0
        Bubble.__init__(self, images.sprget(nimages[0]), x, y)
        self.gen.append(self.normal_movements(dx=dx, dy=dy,
                                              timeout=self.timeout))
        if len(nimages) == 3:
            nimages = [nimages[1], nimages[2], nimages[1], nimages[0]]
        if len(nimages) > 1:
            self.setimages(self.cyclic(nimages))

    def findhole(self, testline):
        holes = [x for x in range(len(testline)-1) if testline[x:x+2]=='  ']
        if not holes:
            holes = range(2, len(testline)-3)
        return random.choice(holes) * CELL


class PlainBubble(BonusBubble):
    timeout = 500
    def condition():
        return boards.curboard.holes

def extend_name(l):
    text = 'extend'
    return text[:l] + text[l].upper() + text[l+1:]

class LetterBubble(BonusBubble):
    max = 2
    def condition():
        return boards.curboard.letter
    def __init__(self, pn, l=None):
        if l is None:
            l = random.randint(0,5)
        self.l = l
        lettername = extend_name(self.l)
        BonusBubble.__init__(self, pn, nimages=getattr(LetterBubbles, lettername))
    def popped(self, dragon):
        if dragon:
            dragon.bubber.giveletter(self.l)
        return 50

class FireFlame(ActiveSprite):
    def __init__(self, x0, y0, poplist, dirs=None, countdown=0):
        ico = images.sprget(Fire.ground[0])
        ActiveSprite.__init__(self, ico, x0*CELL, y0*CELL)
        if not countdown:
            dirs = []
        self.poplist = poplist
        self.gen.append(self.burning(dirs, countdown))
        self.setimages(self.cyclic(Fire.ground, 1))
    def burning(self, dirs, countdown):
        from monsters import Monster
        x0 = self.x//CELL
        y0 = self.y//CELL
        for dir in dirs:
            if bget(x0+dir, y0+1) == '#' and bget(x0+dir, y0) == ' ':
                FireFlame(x0+dir, y0, self.poplist, [dir], countdown-1)
        for i in range(17):
            yield None
            for s in self.touching(0):
                if isinstance(s, Monster):
                    s.argh(self.poplist)
            yield None
        self.kill()

class FireDrop(ActiveSprite):
    def __init__(self, x, y, poplist=None):
        ActiveSprite.__init__(self, images.sprget(Fire.drop), x, y)
        self.poplist = poplist or [None]
        self.gen.append(self.dropping())
    def dropping(self):
        x0 = self.x//CELL
        while bget(x0, self.y//CELL) == '#' or bget(x0, self.y//CELL+1) != '#':
            if self.y >= boards.bheight:
                self.kill()
                return
            self.move(self.x, (self.y + 8) & ~7)
            yield None
        y0 = self.y//CELL
        if bget(x0-1, y0) == ' ':
            FireFlame(x0, y0, self.poplist, [-1, 1], 5)
        self.kill()

class FireBubble(BonusBubble):
    max = 4
    nimages = GreenAndBlue.fire_bubbles
    def condition():
        return boards.curboard.fire
    def popped(self, dragon):
        if dragon:
            x0 = self.x // CELL + 1
            FireDrop(x0*CELL, self.y)
        return 10

class WaterCell(ActiveSprite):
    TESTLIST = [(-1,0), (1,0), (0,1), (0,-1)]
    ICONS = [Water.v_flow,
             Water.start_left,
             Water.start_right,
             Water.h_flow,
             Water.top,
             Water.tr_corner,
             Water.tl_corner,
             Water.h_flow,
             
             Water.bottom,
             Water.br_corner,
             Water.bl_corner,
             Water.h_flow,
             Water.v_flow,
             Water.v_flow,
             Water.v_flow,
             Water.v_flow]
    def __init__(self, x, y, dir, cells, cells2, delay, poplist):
        self.dir = dir
        self.ping = 0
        self.cells = cells
        self.cells2 = cells2
        self.poplist = poplist
        ActiveSprite.__init__(self, images.sprget(Water.top), x, y)
        key = x//CELL, y//CELL
        cells[key] = cells.get(key, 0) + 1
        cells2.append(self)
        self.take_with_me = []
        self.pending = 1
        self.gen.append(self.waiting(delay))
    def waiting(self, delay):
        for i in range(delay):
            yield None
        self.pending = 0
        self.gen.append(self.flooding())
    def onestep(self):
        x0 = self.x // CELL
        y0 = self.y // CELL
        self.cells[x0, y0] -= 1
        if bget(x0, y0+1) == ' ':
            dx, dy = 0, 1
            if self.y + CELL > boards.bheight:
                self.kill()
                self.pending = -1
                return
            self.ping = 0
        elif bget(x0+self.dir, y0) == ' ':
            dx, dy = self.dir, 0
        elif bget(x0-self.dir, y0) == ' ':
            self.ping += 1
            if self.ping == 3:
                self.kill()
                self.pending = -1
                return
            self.dir = -self.dir
            dx, dy = self.dir, 0
        else:
            self.kill()
            self.pending = -1
            return
        x0 += dx
        y0 += dy
        self.cells[x0, y0] = self.cells.get((x0, y0), 0) + 1
        self.pending = x0, y0
    def flooding(self):
        from monsters import Monster
        self.touchable = 1
        while self.pending != -1:
            if self.pending == 0:
                for c in self.cells2:
                    if c.pending == 0:
                        c.onestep()
            #l = [(k,v) for k,v in self.cells.items() if v]
            #l.sort()
            #print (self.x//CELL, self.y//CELL), l
            if self.pending == -1:
                break
            x0, y0 = self.pending
            self.pending = 0
            flag = 0
            for k in range(4):
                dx, dy = self.TESTLIST[k]
                if self.cells.get((x0+dx, y0+dy)):
                    flag += 1<<k
            ico = images.sprget(self.ICONS[flag])
            x0 *= CELL
            y0 *= CELL
            for s in self.touching(0):
                if isinstance(s, Monster):
                    s.untouchable()
                    s.gen = []
                    self.take_with_me.append(s)
                elif isinstance(s, Bubble):
                    s.pop(self.poplist)
            for s in self.take_with_me:
                if s.alive:
                    s.move(x2bounds(x0-HALFCELL), y0-CELL)
            self.move(x0, y0, ico)
            yield None
        self.cells2.remove(self)
    def kill(self):
        from monsters import Monster
        for s in self.take_with_me[:]:
            if isinstance(s, Monster) and s.alive:
                s.argh(self.poplist, onplace=1)
        del self.take_with_me[:]
        ActiveSprite.kill(self)
    def touched(self, dragon):
        #self.untouchable()
        #self.take(player)
        dragon.watermove(x2bounds(self.x-HALFCELL), self.y-CELL+1)
        return 1
    #def take(self, s):
    #    for c in self.cells2:
    #        if s in c.take_with_me:
    #            return
    #    self.take_with_me.append(s)

class WaterBubble(BonusBubble):
    max = 4
    nimages = GreenAndBlue.water_bubbles
    def condition():
        return boards.curboard.water
    def popped(self, dragon):
        if dragon:
            x0 = self.x // CELL + 1
            y0 = self.y // CELL + 1
            if bget(x0,y0) == '#':
                if bget(x0+1,y0) == '#':
                    y0 += 1
                    if bget(x0,y0) == '#':
                        #if bget(x0+1,y0) == '#':
                        #    return
                        x0 += 1
                else:
                    x0 += 1
            cells = {}
            cells2 = []
            dir = random.choice([-1, 1])
            poplist = [None]
            for i in range(20):
                WaterCell(x0*CELL, y0*CELL, dir, cells, cells2, i, poplist)
        return 10

class FiredLightning(ActiveSprite):
    def __init__(self, x, y, dir):
        ActiveSprite.__init__(self, images.sprget(Lightning.fired), x, y)
        self.dir = 13*dir
        self.gen.append(self.moving())
    def moving(self):
        from monsters import Monster
        poplist = [None]
        while -2*CELL < self.x < boards.bwidth:
            for s in self.touching(2):
                if isinstance(s, Monster):
                    s.argh(poplist)
                elif isinstance(s, Bubble):
                    s.pop(poplist)
            self.step(self.dir, 0)
            yield None
        self.kill()

class LightningBubble(BonusBubble):
    max = 4
    nimages = GreenAndBlue.light_bubbles
    def condition():
        return boards.curboard.lightning
    def popped(self, dragon):
        if dragon:
            FiredLightning(self.x, self.y, -dragon.dir)
        return 10

class SpinningBall(ActiveSprite):
    def __init__(self, x, y, poplist):
        ActiveSprite.__init__(self, images.sprget(SpinningBalls.free[0]), x, y)
        self.poplist = poplist
        self.gen.append(self.dropping())
        self.setimages(self.cyclic(SpinningBalls.free[1:], 2))
        self.touchable = 1
    def dropping(self):
        from monsters import Monster
        for ny in range(self.y, boards.bheight, 5):
            self.move(self.x, ny)
            yield None
            for s in self.touching(0):
                if isinstance(s, Monster):
                    s.argh(self.poplist)
                elif isinstance(s, Bubble):
                    s.pop(self.poplist)
        self.kill()
    def touched(self, dragon):
        dragon.die()

class StarBubble(BonusBubble):
    timeout = 250
    names = [k for k in Stars.__dict__.keys() if not k.startswith('_')]
    def __init__(self, pn):
        self.colorname = random.choice(StarBubble.names)
        BonusBubble.__init__(self, pn, [('starbub', self.colorname, i)
                                        for i in range(3)])
##    def __init__(self, pn):
##        BonusBubble.__init__(self, pn)
##        self.colorname = random.choice(StarBubble.names)
##        starimg = [('smstar', self.colorname, 0),
##                   ('smstar', self.colorname, 1)]
##        smallstar = ActiveSprite(images.sprget(starimg[-1]),
##                                 self.x+8, self.y+8)
##        smallstar.setimages(smallstar.cyclic(starimg))
##        smallstar.gen.append(smallstar.following(self, 8, 8))
    def popped(self, dragon):
        if dragon:
            from bonuses import BonusMaker, AllOutcomes
            BonusMaker(self.x, self.y, getattr(Stars, self.colorname),
                       outcome=random.choice(AllOutcomes))
        return 100

class MonsterBubble(BonusBubble):
    timeout = 100
    def __init__(self, pn, mcls):
        import monsters, mnstrmap
        BonusBubble.__init__(self, pn)
        mdef = getattr(mnstrmap, mcls.__name__)
        m = mcls(mdef, self.x, self.y, 1)
        m.in_bubble(self)

Classes = ([PlainBubble] * 7 +
           [FireBubble, WaterBubble, LightningBubble] * 4 +
           [LetterBubble])

def newbubble(): #force=0):
    #if force:
    #cls = PlainBubble
    #else:
    cls = random.choice(Classes)
    if not cls.__dict__['condition']():
        return
    if cls.max is not None:
        others = [s for s in images.ActiveSprites if isinstance(s, cls)]
        if len(others) >= cls.max:
            return
    sendbubble(cls)

def sendbubble(cls, *args):
    from player import BubPlayer
    players = [p for p in BubPlayer.PlayerList if p.isplaying()]
    if not players:
        return
    pn = random.choice(players).pn
    cls(pn, *args)

def newbonusbubble():
    boards.curboard.top = random.choice([0,0,0, 1,1,1, 2,2, 3,3])
    r = random.random()
    if r < 0.14:
        sendbubble(random.choice(Classes))
    elif r < 0.16:
        from player import BubPlayer
        import monsters
        mcls = random.choice(monsters.MonsterClasses)
        for d in BubPlayer.DragonList:
            sendbubble(MonsterBubble, mcls)
    else:
        sendbubble(StarBubble)
