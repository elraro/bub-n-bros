from __future__ import generators
import random
import gamesrv
import images
import boards
from boards import *
from images import ActiveSprite
from mnstrmap import GreenAndBlue, Bonuses, Diamonds, Stars, BigImages
from mnstrmap import PotionBonuses, Fire
from player import BubPlayer


questionmarklist = ['questionmark3',
                    'questionmark4',
                    'questionmark5',
                    'questionmark4',
                    'questionmark3',
                    'questionmark2',
                    'questionmark1',
                    'questionmark2']

class Bonus(ActiveSprite):
    bubblable = 1
    touchable = 1
    points = 750
    timeout = 250
    sound = 'Fruit'

    def __init__(self, x, y, nimage=None, points=None, falling=1):
        if nimage is not None:
            self.nimage = nimage
        if points is not None:
            self.points = points
        ActiveSprite.__init__(self, images.sprget(self.nimage), x, y)
        self.taken_by = []
        self.gen.append(self.timeouter())
        if falling:
            self.gen.append(self.faller())

    def buildoutcome(self):
        return (self.__class__,)

    def faller(self):
        while self.y < boards.bheight:
            if onground(self.x, self.y):
                yield None
                yield None
            else:
                self.move(self.x, (self.y+4) & ~3)
            yield None
        self.kill()

    def timeouter(self):
        for i in range(self.timeout):
            yield None
        self.kill()

    def touched(self, dragon):
        if (dragon.x + dragon.ico.w > self.x + 10   and
            dragon.y + dragon.ico.h > self.y + 8    and
            self.x + self.ico.w     > dragon.x + 10 and
            self.y + self.ico.h     > dragon.y + 10):
            if not self.taken_by:
                self.gen = [self.taking()]
                if self.sound:
                    self.play(getattr(images.Snd, self.sound))
            if dragon not in self.taken_by:
                self.taken_by.append(dragon)

    def taking(self, follow_dragons=0, delay=1):
        for t in range(delay):
            yield None   # time to be taken by several dragons
        if self.points:
            for p in self.taken_by:
                if follow_dragons and p.alive:
                    s = p
                else:
                    s = self
                points(s.x + s.ico.w//2, s.y + s.ico.h//2 - CELL, p, self.points)
        if self.taken1(self.taken_by) != -1:
            self.kill()

    def taken1(self, dragons):
        for d in dragons[:]:
            if d.alive:
                self.taken(d)

    def taken(self, dragon):
        pass

    def endaction(self, dragon):
        pass

    def in_bubble(self, bubble):
        self.untouchable()
        bubble.move(self.x, self.y)
        bubble.to_front()
        self.to_front()
        self.gen = [self.bubbling(bubble, self.ico)]
        self.move(bubble.x+8, bubble.y+8, images.sprget('questionmark3'))
        self.setimages(self.cyclic(questionmarklist, 2))

    def bubbling(self, bubble, ico):
        #dx = (bubble.ico.w - nico.w) // 2
        #dy = (bubble.ico.h - nico.h) // 2
        #dx = [dx, dx+1, dx, dx-1]
        #i = 0
        #while not hasattr(bubble, 'poplist'):
        #    self.move(bubble.x+dx[i//4], bubble.y+dy, nico)
        #    i = (i+1) % 16
        #    yield None
        while not hasattr(bubble, 'poplist'):
            self.move(bubble.x+8, bubble.y+8)
            yield None
        if bubble.poplist is not None:
            dragon = bubble.poplist[0]
            if dragon is not None:
                self.play(images.Snd.Yippee)
                if dragon not in self.taken_by:
                    self.taken_by.append(dragon)
                if self.points > 10:
                    dragon.bubber.givepoints(self.points - 10)
                    pn = dragon.bubber.pn
                    if self.points in GreenAndBlue.points[pn]:
                        Points(bubble.x + bubble.ico.w//2, bubble.y, pn, self.points)
                self.taken1(BubPlayer.DragonList)
                p = Parabolic(ico, bubble.x, bubble.y)
                p.gen.append(p.moving(-1.0))
        self.kill()


def points(x, y, dragon, points):
    dragon.bubber.givepoints(points)
    pn = dragon.bubber.pn
    if points in GreenAndBlue.points[pn]:
        Points(x, y, pn, points)

class Points(ActiveSprite):

    def __init__(self, x, y, pn, points):
        ico = images.sprget(GreenAndBlue.points[pn][points])
        ActiveSprite.__init__(self, ico, x - ico.w//2, max(8, y))
        self.nooverlap = 1
        self.gen.append(self.raiser())

    def raiser(self):
        wait = 0
        for s in images.ActiveSprites:
            if s is self:
                break
            if (isinstance(s, Points) and s.nooverlap and
                abs(self.x-s.x)<self.ico.w*2//3 and
                abs(self.y-s.y)<self.ico.h):
                wait += 5
        for t in range(wait):
            yield None
        for i in range(25):
            if i == 7:
                self.nooverlap = 0
            self.step(0, -2)
            yield None
            if self.y <= 0:
                break
        for i in range(20):
            yield None
        self.kill()


class Parabolic(ActiveSprite):
    fallstraight = 0
    
    def moving(self, y_amplitude = -8.0):
        dxy = [(random.random()-0.5) * 15.0,
               (random.random()+0.5) * y_amplitude]
        for n in self.parabolic(dxy):
            yield n
            if dxy[1] >= 4.0 and self.fallstraight:
                self.gen.append(self.falling())
                return
        self.kill()

    def falling(self):
        nx = self.x
        ny = self.y & ~3
        while not onground(nx, ny):
            ny += 4
            if ny >= boards.bheight:
                ny -= boards.bheightmod
            self.move(nx, ny)
            yield None
        self.build()
        self.kill()

    def killmonsters(self, poplist):
        from monsters import Monster
        while 1:
            for s in self.touching(0):
                if isinstance(s, Monster):
                    s.argh(poplist)
            yield None

    def build(self):
        pass


class Parabolic2(Parabolic):
    points = 0

    def __init__(self, x, y, imglist, imgspeed=3, onplace=0, y_amplitude=-8.0):
        Parabolic.__init__(self, images.sprget(imglist[0]), x, y)
        if onplace:
            self.gen.append(self.falling())
        else:
            self.gen.append(self.moving(y_amplitude))
        if len(imglist) > 1:
            self.setimages(self.cyclic(imglist, imgspeed))

    def touched(self, dragon):
        if self.points:
            points(self.x + self.ico.w/2, self.y + self.ico.h/2 - CELL,
                   dragon, self.points)
            self.kill()


class BonusMaker(Parabolic2):
    fallstraight = 1
    touchable = 1

    def __init__(self, x, y, imglist, imgspeed=3, onplace=0, outcome=None):
        assert outcome
        self.outcome = outcome
        Parabolic2.__init__(self, x, y, imglist, imgspeed, onplace)

    def build(self):
        cls = self.outcome[0]
        args = self.outcome[1:]
        if issubclass(cls, RandomBonus) and not boards.curboard.playingboard:
            return None
        else:
            return cls(self.x, self.y, *args)

    def touched(self, dragon):
        pass


class MonsterBonus(Bonus):

    def __init__(self, x, y, multiple):
        self.level = multiple
        if multiple >= len(Bonuses.monster_bonuses):
            multiple = len(Bonuses.monster_bonuses) - 1
        Bonus.__init__(self, x, y, *Bonuses.monster_bonuses[multiple])

    def buildoutcome(self):
        return (MonsterBonus, self.level)

    def taken(self, dragon):
        dragon.carrybonus(self, 543)


class RandomBonus(Bonus):
    timeout = 500


class Shoe(RandomBonus):
    "Fast Runner. Cumulative increase of horizontal speed."
    nimage = Bonuses.shoe
    def taken(self, dragon):
        dragon.dcap['hspeed'] += 1
        dragon.carrybonus(self)

class Coffee(RandomBonus):
    "Caffeine. Cumulative increase of the horizontal speed and fire rate."
    nimage = Bonuses.coffee
    def taken(self, dragon):
        dragon.dcap['hspeed'] += 0.5
        dragon.dcap['firerate'] += 1
        dragon.carrybonus(self)

class Butterfly(RandomBonus):
    "Lunar Gravity. Allows you to jump twice as high as before."
    nimage = Bonuses.butterfly
    def taken(self, dragon):
        dragon.dcap['gravity'] *= 0.5
        dragon.carrybonus(self)

class Cocktail(RandomBonus):
    "Short Lived Bubbles. Makes your bubbles explode more quickly."
    nimage = Bonuses.cocktail
    points = 2000
    def taken(self, dragon):
        dragon.dcap['bubbledelay'] = 1
        dragon.carrybonus(self)

class Extend(RandomBonus):
    "E X T E N D. Gives you your missing letters and clear the level. "
    nimage = Bonuses.extend
    points = 0
    def taken(self, dragon):
        from bubbles import extend_name
        names = [extend_name(l) for l in range(6)]
        missing = [name for name in names if name not in dragon.bubber.letters]
        points(dragon.x + dragon.ico.w//2, dragon.y, dragon, 10000 * len(missing))
        for l in range(6):
            if extend_name(l) in missing:
                dragon.bubber.giveletter(l, promize=0)

class HeartPoison(RandomBonus):
    "Heart Poison. Freeze all free monsters."
    nimage = Bonuses.heart_poison
    def taken1(self, dragons):
        import monsters
        monsters.freeze_em_all()

class VioletNecklace(RandomBonus):
    "Monster Duplicator. Double the number of free monsters."
    points = 650
    nimage = Bonuses.violet_necklace
    def taken1(self, dragons):
        for s in BubPlayer.MonsterList[:]:
            if s.regular():
                s.__class__(s.mdef, s.x, s.y, -s.dir)

class WandBonus(RandomBonus):
    Modes = [
        (Bonuses.brown_wand,   750,  Bonuses.cyan_ice,    700,  BigImages.cyan_ice,    20000),
        (Bonuses.yellow_wand,  750,  Bonuses.violet_ice,  750,  BigImages.violet_ice,  20000),
        (Bonuses.green_wand,   750,  Bonuses.peach2,      800,  BigImages.peach2,      30000),
        (Bonuses.violet_wand,  750,  Bonuses.pastec2,     850,  BigImages.pastec2,     30000),
        (Bonuses.blue_wand,    750,  Bonuses.cream_pie,   900,  BigImages.cream_pie,   40000),
        (Bonuses.red_wand,     750,  Bonuses.sugar_pie,   950,  BigImages.sugar_pie,   40000),
        (Bonuses.violet_chest, 2000, Diamonds.violet,     6000, BigImages.violet,      60000),
        (Bonuses.blue_chest,   2000, Diamonds.blue,       7000, BigImages.blue,        60000),
        (Bonuses.red_chest,    2000, Diamonds.red,        8000, BigImages.red,         70000),
        (Bonuses.yellow_chest, 2000, Diamonds.yellow,     9000, BigImages.yellow,      70000),
        ]
    def __init__(self, x, y):
        self.mode = random.choice(WandBonus.Modes)
        RandomBonus.__init__(self, x, y, *self.mode[:2])
    def taken1(self, dragons):
        BubPlayer.BubblesBecome = self.bubble_outcome
        BubPlayer.MegaBonus     = self.mega_bonus
    def bubble_outcome(self, bubble):
        if bubble.pop():
            x = bubble.x
            if x < 2*CELL:
                x = 2*CELL
            elif x > boards.bwidth - 4*CELL:
                x = boards.bwidth - 4*CELL
            Bonus(x, bubble.y, *self.mode[2:4])
    def mega_bonus(self):
        nico, npoints = self.mode[4:6]
        ico = images.sprget(nico)
        x = random.randrange(0, boards.bwidth-ico.w)
        mb = Megabonus(x, -ico.h, nico, npoints)
WandBonus1 = WandBonus  # increase probability

class Megabonus(Bonus):
    touchable = 0
    bubblable = 0
    sound = 'Extra'
    def faller(self):
        for t in range(71):
            yield None
        ymax = boards.bheight - CELL - self.ico.h
        while self.y < ymax:
            self.step(0, 6)
            yield None
            self.touchable = 1


def starexplosion(x, y, multiplyer, killmonsters=0, outcomes=[]):
    outcomes = list(outcomes)
    poplist = [None]
    for i in range(multiplyer):
        items = Stars.__dict__.items()
        random.shuffle(items)
        for key, value in items:
            if not key.startswith('_'):
                if outcomes:
                    BonusMaker(x, y, value, outcome=outcomes.pop())
                else:
                    b = Parabolic2(x, y, value)
                    if killmonsters:
                        b.gen.append(b.killmonsters(poplist))

class Book(RandomBonus):
    "Magic Bomb. Makes a magical explosion."
    points = 2000
    nimage = Bonuses.book
    def taken1(self, dragons):
        starexplosion(self.x, self.y, 1, killmonsters=1)

class Potion(RandomBonus):
    Potions = [(Bonuses.red_potion,    150,
                     [(PotionBonuses.coin, 350), (PotionBonuses.rainbow, 600)]),
               (Bonuses.green_potion,  350,
                     [(PotionBonuses.flower, 1000), (PotionBonuses.trefle, 2000)]),
               (Bonuses.yellow_potion, 550,
                     [(PotionBonuses.green_note, 2000), (PotionBonuses.blue_note, 3000)]),
               ]
    def __init__(self, x, y):
        self.mode = random.choice(Potion.Potions)
        RandomBonus.__init__(self, x, y, *self.mode[:2])
    def taken1(self, dragons):
        blist = self.mode[2]
        if random.random() < 0.6:
            blist = [random.choice(blist)]
        boards.replace_boardgen(boards.potion_fill(blist))

class Hamburger(RandomBonus):
    "Fire Bubbles. Makes you fire napalm bubbles."
    nimage = Bonuses.hamburger
    def taken(self, dragon):
        dragon.dcap['shootbubbles'] = ['FireBubble'] * 10
        dragon.carrybonus(self)

class Beer(RandomBonus):
    "Water Bubbles. Your bubbles will now be filled with water."
    nimage = Bonuses.beer
    def taken(self, dragon):
        dragon.dcap['shootbubbles'] = ['WaterBubble'] * 10
        dragon.carrybonus(self)

class FrenchFries(RandomBonus):
    "Lightning Bubbles."
    nimage = Bonuses.french_fries
    def taken(self, dragon):
        dragon.dcap['shootbubbles'] = ['LightningBubble'] * 10
        dragon.carrybonus(self)

class Door(RandomBonus):
    points = 1000
    nimage = Bonuses.door
    def taken1(self, dragons):
        starexplosion(self.x, self.y, 2,
                      outcomes = [(MonsterBonus, -1)] * 10)

class SoftIce1(RandomBonus):
    "Long Fire. Increase the range of your bubble throw out."
    nimage = Bonuses.softice1
    def taken(self, dragon):
        dragon.dcap['shootthrust'] *= 1.5
        dragon.carrybonus(self)

class SoftIce2(RandomBonus):
    "Short Fire. Shorten the range of your bubble throw out."
    nimage = Bonuses.softice2
    points = 300
    def taken(self, dragon):
        dragon.dcap['shootthrust'] /= 1.5
        dragon.carrybonus(self)

class CustardPie(RandomBonus):
    "High Speed Fire. Increase your fire rate."
    nimage = Bonuses.custard_pie
    points = 700
    def taken(self, dragon):
        dragon.dcap['firerate'] += 1.5
        dragon.carrybonus(self)

class TemporaryBonus(RandomBonus):
    def taken(self, dragon):
        dragon.dcap[self.capname] += 1
        dragon.carrybonus(self, self.captime)
    def endaction(self, dragon):
        if dragon.dcap[self.capname] >= 1:
            dragon.dcap[self.capname] -= 1

class Mushroom(TemporaryBonus):
    "Bouncy Bouncy. Makes you jump continuously."
    nimage = Bonuses.mushroom
    points = 900
    capname = 'pinball'
    captime = 625

class Rape(TemporaryBonus):
    "Auto Fire. Makes you fire continuously."
    nimage = Bonuses.rape
    points = 800
    capname = 'autofire'
    captime = 675

class Insect(RandomBonus):
    "Crush World."
    nimage = Bonuses.insect
    def taken1(self, dragons):
        boards.extra_boardgen(boards.extra_walls_falling())

class Ring(TemporaryBonus):
    "The One Ring."
    nimage = Bonuses.ring
    points = 4000
    capname = 'ring'
    captime = 700

class GreenPepper(TemporaryBonus):
    "Hot Pepper. Run! Run! That burns."
    nimage = Bonuses.green_pepper
    capname = 'hotstuff'
    captime = 100

class Lollipop(RandomBonus):
    "Yo Man! Makes you walk backward."
    nimage = Bonuses.lollipop
    def taken(self, dragon):
        dragon.dcap['left2right'] = -dragon.dcap['left2right']
        dragon.carrybonus(self)

class Chickpea(RandomBonus):
    "Basilik. Allows you to touch the monsters."
    nimage = Bonuses.chickpea
    points = 800
    def taken(self, dragon):
        dragon.dcap['shield'] = 200
        dragon.carrybonus(self, 200)

class IceCream(RandomBonus):
    IceCreams = [(Bonuses.icecream6,  250),
                 (Bonuses.icecream5,  500),
                 (Bonuses.icecream4,  1000),
                 (Bonuses.icecream3,  2000)]
    def __init__(self, x, y, generation=0):
        self.generation = generation
        RandomBonus.__init__(self, x, y, *self.IceCreams[generation])
    def taken1(self, dragons):
        nextgen = self.generation + 1
        if nextgen < len(self.IceCreams):
            for i in range(2):
                x, y = chooseground(200)
                if x is None:
                    return
                IceCream(x, y, nextgen)

class Grenade(RandomBonus):
    "Barbecue."
    nimage = Bonuses.grenade
    points = 550
    def taken1(self, dragons):
        from bubbles import FireFlame
        poplist = [None]
        for y in range(1, boards.height-1):
            for x in range(2, boards.width-2):
                if bget(x,y) == ' ' and bget(x,y+1) == '#':
                    FireFlame(x, y, poplist)

class Conch(RandomBonus):
    "Sea Shell. Let's bring the sea here!"
    nimage = Bonuses.conch
    points = 650
    def taken1(self, dragons):
        boards.extra_boardgen(boards.extra_water_flood())

##class Umbrella(RandomBonus):
##    Umbrellas = [(Bonuses.brown_umbrella,  2),
##                 (Bonuses.grey_umbrella,   3),
##                 (Bonuses.violet_umbrella, 4)]
##    points = 0
##    def __init__(self, x, y):
##        self.mode = random.choice(Umbrella.Umbrellas)
##        RandomBonus.__init__(self, x, y, self.mode[0])
##    def taken1(self, dragons):
##        boards.replace_boardgen(boards.umbrella(self, self.mode[1]))
##        return -1

def fire_rain(x, poplist):
    from bubbles import FireDrop
    FireDrop(x, -CELL, poplist)

def water_rain(x, poplist):
    from bubbles import WaterCell
    cells = {}
    cells2 = []
    dir = random.choice([-1, 1])
    for i in range(5):
        WaterCell(x, 0, dir, cells, cells2, i, poplist)

def ball_rain(x, poplist):
    from bubbles import SpinningBall
    SpinningBall(x, -CELL, poplist)

class Umbrella(RandomBonus):
    Umbrellas = [(Bonuses.brown_umbrella,  900,  fire_rain,  10, 60),
                 (Bonuses.grey_umbrella,   950,  water_rain, 5,  60),
                 (Bonuses.violet_umbrella, 1000, ball_rain,  9, 120)]
    def __init__(self, x, y):
        self.mode = random.choice(Umbrella.Umbrellas)
        RandomBonus.__init__(self, x, y, *self.mode[:2])
    def taken1(self, dragons):
        boards.extra_boardgen(self.raining())
    def raining(self):
        builder, drops, timemax = self.mode[2:]
        times = [random.randrange(0, timemax) for i in range(drops)]
        poplist = [None]
        for t in range(timemax):
            for i in range(times.count(t)):
                x = random.randrange(2*CELL, bwidth-3*CELL+1)
                builder(x, poplist)
            yield 0

class Fruits(RandomBonus):
    bubblable = 0
    sound = 'Extra'
    Fruits = [(Bonuses.kirsh,      100),
              #(Bonuses.icecream1,  150),
              (Bonuses.erdbeer,    150),
              #(Bonuses.fish1,      250),
              (Bonuses.tomato,     200),
              #(Bonuses.donut,      250),
              (Bonuses.apple,      250),
              (Bonuses.corn,       300),
              #(Bonuses.icecream2,  600),
              (Bonuses.radish,     350),
              ]
    def __init__(self, x, y):  # x and y ignored !
        fine = 0
        for i in range(20):
            x0 = random.randint(3, boards.width-5)
            y0 = random.randint(1, boards.height-3)
            for xt in range(x0-1, x0+3):
                if xt == x0-1 or xt == x0+2:
                    yplus = 1
                else:
                    yplus = 0
                for yt in range(y0+yplus, y0+4-yplus):
                    if bget(xt,yt) != ' ':
                        break
                else:
                    continue
                break
            else:
                x, y = x0*CELL, y0*CELL
                fine = 1
                break
        mode = random.choice(Fruits.Fruits)
        RandomBonus.__init__(self, x, y, falling=0, *mode)
        self.repeatcount = 0
        if not fine:
            self.kill()
        elif random.random() < 0.04:
            self.superfruit = mode
            self.sound = 'Shh'
            self.points = 0
            self.repeatcount = random.randrange(50,100)
    def taken1(self, dragons):
        if self.repeatcount:
            image, points = self.superfruit
            f = Parabolic2(self.x, self.y, [image], y_amplitude = -1.5)
            f.points = points
            f.touchable = 1
            self.repeatcount -= 1
            self.gen.append(self.taking(1, 2))
            return -1
Fruits1 = Fruits  # increase probability
Fruits2 = Fruits
Fruits3 = Fruits
Fruits4 = Fruits
Fruits5 = Fruits
Fruits6 = Fruits

class BlueNecklace(RandomBonus):
    "Self Duplicator. Mirror yourself."
    points = 1000
    nimage = Bonuses.blue_necklace
    def taken(self, dragon):
        from player import Dragon
        d = Dragon(dragon.bubber, dragon.x, dragon.y, -dragon.dir, dragon.dcap)
        d.dcap['left2right'] = -d.dcap['left2right']
        d.up = dragon.up
        s = (dragon.dcap['shield'] + 12) & ~3
        dragon.dcap['shield'] = s+2
        d.dcap['shield'] = s
        dragon.bubber.dragons.append(d)
        d1 = random.choice((d, dragon))
        d1.carrybonus(self, 250)

class Monsterer1(RandomBonus):
    "Monsterificator. Let's play on the other side!"
    points = 800
    nimage = Bonuses.red_crux
    mlist = ['Nasty', 'Monky', 'Springy', 'Orcy']
    def taken(self, dragon):
        mcls = random.choice(self.mlist)
        dragon.become_monster(mcls)

class Monsterer2(Monsterer1):
    "Monsterificator. Let's play on the other side!"
    points = 850
    nimage = Bonuses.blue_crux
    mlist = ['Ghosty', 'Flappy', 'Gramy', 'Blitzy']

class Bubblizer(RandomBonus):
    "Bubblizer."
    points = 750
    nimage = Bonuses.gold_crux
    def taken(self, dragon):
        from bubbles import FireBubble, WaterBubble, LightningBubble
        bcls = random.choice([FireBubble, WaterBubble, LightningBubble])
        b = bcls(dragon.bubber.pn)
        b.move(dragon.x, dragon.y)
        if not dragon.become_bubblingeyes(b):
            b.kill()

class Carrot(RandomBonus):
    "Angry Monster. Turns all free monsters angry."
    nimage = Bonuses.carrot
    points = 950
    def taken1(self, dragons):
        from monsters import Monster
        for s in images.ActiveSprites:
            if isinstance(s, Monster) and s.regular():
                s.angry = 1
                s.resetimages()

class Egg(RandomBonus):
    "Teleporter. Exchange yourself with somebody else."
    nimage = Bonuses.egg
    def taken1(self, dragons):
        dragons = [d for d in dragons if d in d.bubber.dragons]
        alldragons = [d for d in BubPlayer.DragonList if d in d.bubber.dragons]
        others = [d for d in alldragons if d not in dragons]
        xchg = {}
        random.shuffle(dragons)
        random.shuffle(others)
        while dragons and others:
            d1 = dragons.pop()
            d2 = others.pop()
            xchg[d1] = d2.bubber
            xchg[d2] = d1.bubber
        if len(dragons) > 1:
            copy = dragons[:]
            for i in range(10):
                random.shuffle(copy)
                for j in range(len(dragons)):
                    if dragons[j] == copy[j]:
                        break
                else:
                    break
            for d1, d2 in zip(dragons, copy):
                xchg[d1] = d2.bubber
        for d1, bubber2 in xchg.items():
            d1.bubber.dragons.remove(d1)
            d1.bubber = bubber2
            bubber2.dragons.append(d1)
            d1.dcap['shield'] = 50

class Bomb(RandomBonus):
    "Baaoouuuummmm! Explode that wall!"
    nimage = Bonuses.bomb
    def taken1(self, dragons):
        RADIUS = 3.9 * CELL
        Radius2 = RADIUS * RADIUS
        brd = boards.curboard
        cx = self.x + HALFCELL
        cy = self.y + HALFCELL - RADIUS/2
        for y in range(0, brd.height):
            dy1 = abs(y*CELL - cy)
            dy2 = abs((y-(brd.height-1))*CELL - cy)
            dy3 = abs((y+(brd.height-1))*CELL - cy)
            dy = min(dy1, dy2, dy3)
            for x in range(2, brd.width-2):
                dx = x*CELL - cx
                if dx*dx + dy*dy < Radius2:
                    try:
                        brd.killwall(x,y)
                    except KeyError:
                        pass
        brd.reorder_walls()
        starexplosion(self.x, self.y, 2)

class Ham(RandomBonus):
    "Protein. Let's build something!"
    nimage = Bonuses.ham
    def taken1(self, dragons):
        RADIUS = 3.9 * CELL
        Radius2 = RADIUS * RADIUS
        brd = boards.curboard
        cx = self.x + HALFCELL
        cy = self.y + HALFCELL - RADIUS/2
        xylist = []
        for y in range(0, brd.height):
            dy1 = abs(y*CELL - cy)
            dy2 = abs((y-(brd.height-1))*CELL - cy)
            dy3 = abs((y+(brd.height-1))*CELL - cy)
            dy = min(dy1, dy2, dy3)
            for x in range(2, brd.width-2):
                dx = x*CELL - cx
                if dx*dx + dy*dy < Radius2:
                    if (y,x) not in brd.walls_by_pos and random.random() < 0.5:
                        brd.putwall(x,y)
                        xylist.append((x, y))
        brd.reorder_walls()
        boards.extra_boardgen(boards.single_blocks_falling(xylist))

class Chestnut(RandomBonus):
    "Relativity. Speed up or slow down the game."
    nimage = Bonuses.chestnut
    sound = None
    def taken1(self, dragons):
        boards.set_frametime(random.choice((0.5, 2.0)))
        BubPlayer.MultiplyerReset = BubPlayer.FrameCounter + 500
        self.play(images.Snd.Fruit)


try:
    import statesaver
except ImportError:
    print "'statesaver' module not compiled, no clock bonus"
else:
    import new
    def standard_build(self):
        return new.instance(self.__class__)
    boards.Board.inst_build = standard_build
    gamesrv.Sprite.inst_build = standard_build
    
    class Clock(RandomBonus):
        "Time Machine. Let's do it again!"
        touchable = 0
        points = 0
        nimage = Bonuses.clock
        def __init__(self, x, y):
            RandomBonus.__init__(self, -boards.bwidth, 0)
            #print "starting clock"
            self.savedstate = None
            self.savedscreens = []
            self.gen = [self.delayed_show()]
            boards.extra_boardgen(self.state_saver())
        def delayed_show(self):
            for i in range(10):
                yield None
            if self.savedstate is not None:
                for i in range(55):
                    yield None
                x, y = chooseground(200)
                if x is not None:
                    self.move(x, y)
                    self.touchable = 1
                    self.gen.append(self.timeouter())
                    self.gen.append(self.faller())
                    return
            self.kill()
        def taken1(self, dragons):
            savedstate = self.savedstate
            self.savedstate = None
            if savedstate is not None:
                boards.replace_boardgen(self.state_restorer(savedstate,
                                                            self.savedscreens,
                                                            self))
                self.untouchable()
                return -1

        def state_saver(self):
            # called from BoardGen
            ps = []
            for p1 in BubPlayer.PlayerList:
                if p1.isplaying():
                    d = p1.__dict__.copy()
                    for key in BubPlayer.TRANSIENT_DATA:
                        del d[key]
                    ps.append(d)
                else:
                    ps.append(None)
            topstate = (
                [g for g in boards.BoardGen if not g.gi_running],
                boards.curboard,
                images.ActiveSprites,
                images.SpritesByLoc,
                BubPlayer.__dict__,
                gamesrv.sprites,
                gamesrv.sprites_by_n,
                ps,
                images.Snd.__dict__,
                )
            #import pdb; pdb.set_trace()
            self.savedstate = topstate = statesaver.copy(topstate)

            while self.alive:
                gamesrv.sprites[0] = ''
                data = ''.join(gamesrv.sprites)
                self.savedscreens.append(data)
                yield 0
                yield 0
                self.savedscreens.append(data)
                yield 0
                yield 0
            self.savedscreens = []
        def state_restorer(self, savedstate, savedscreens, blinkme):
            # called from BoardGen
            from player import scoreboard
            status = 0
            for t in range(10):
                if not (t & 1):
                    gamesrv.sprites[0] = ''
                    savedscreens.append(''.join(gamesrv.sprites))
                time = boards.normal_frame()
                for i in range(t):
                    status += 1
                    if status % 3 == 0 and blinkme.alive:
                        if status % 6 == 0:
                            blinkme.step(boards.bwidth, 0)
                        else:
                            blinkme.step(-boards.bwidth, 0)
                    yield time
            yield boards.force_singlegen()
            yield 15.0
            for p1 in BubPlayer.PlayerList:
                del p1.dragons[:]
            delay = 8.5
            gamesrv.clearsprites()
            while savedscreens:
                gamesrv.sprites[:] = ['', savedscreens.pop()]
                if delay > 0.6:
                    delay *= 0.9
                yield delay
            yield 15.0

            (boards.BoardGen,
             boards.curboard,
             images.ActiveSprites,
             images.SpritesByLoc,
             BubPlayer.__dict__,
             gamesrv.sprites,
             gamesrv.sprites_by_n,
             ps,
             images.Snd.__dict__,
             ) = savedstate

            for p, d in zip(BubPlayer.PlayerList, ps):
                if d is None:
                    p.reset()
                else:
                    p.__dict__.update(d)
                if not p.isplaying():
                    p.zarkoff()
            scoreboard()
            yield 2.5

class MultiStones(RandomBonus):
    Stones = [(Bonuses.emerald,    1000),
              (Bonuses.sapphire,   2000),
              (Bonuses.ruby,       3000),
              ]
    def __init__(self, x, y):
        mode = random.choice(MultiStones.Stones)
        RandomBonus.__init__(self, x, y, *mode)
        self.multi = 10
    def taken1(self, dragons):
        self.multi -= len(dragons)
        if self.multi > 0:
            self.taken_by = []
            self.untouchable()
            self.gen.append(self.touchdelay(5))
            return -1     # don't go away

class Slippy(TemporaryBonus):
    "Greased Feet. Do you want some ice skating?"
    nimage = Bonuses.orange_thing
    points = 900
    capname = 'slippy'
    captime = 606

class Aubergine(RandomBonus):
    "Mirror. The left hand is the one with the thumb on the right, right?"
    nimage = Bonuses.aubergine
    def taken(self, dragon):
        dragon.dcap['lookforward'] = -dragon.dcap['lookforward']
        dragon.carrybonus(self)

class WhiteCarrot(TemporaryBonus):
    nimage = Bonuses.white_carrot
    points = 650
    capname = 'fly'
    captime = 650

class Tin(TemporaryBonus):
    nimage = Bonuses.tin
    points = 700
    def taken(self, dragon):
        dragon.angry += 1
        dragon.carrybonus(self, 633)
    def endaction(self, dragon):
        if dragon.angry >= 1:
            dragon.angry -= 1

class Sugar1(Bonus):
    timeout = 2600
    points = 250
    nimage = Bonuses.yellow_sugar
    def taken(self, dragon):
        #if boards.curboard.wastingplay is None:
            dragon.carrybonus(self, 99999)
        #else:
        #    from player import scoreboard
        #    dragon.bubber.bonbons += 1
        #    scoreboard()

class Sugar2(Sugar1):
    timeout = 2500
    points = 500
    nimage = Bonuses.blue_sugar

class GreenThing(RandomBonus):
    points = 1000
    nimage = Bonuses.green_thing
    def taken1(self, dragons):
        starexplosion(self.x, self.y, 3,
                      outcomes = [random.choice([(Sugar1,), (Sugar2,)])
                                  for i in range(18)])

class Megalightning(ActiveSprite):
    def __init__(self, x1, y1, dragon):
        ActiveSprite.__init__(self, images.sprget(BigImages.blitz),
                              gamesrv.playfield.width, gamesrv.playfield.height)
        self.gen.append(self.moving_to(x1, y1, dragon))
    def moving_to(self, x1, y1, dragon):
        from monsters import Monster
        from bubbles import Bubble
        x0 = self.x
        y0 = self.y
        poplist = [dragon]
        x1 += CELL - self.ico.w//2
        y1 += CELL - self.ico.h//2
        deltax = x1 - x0
        if deltax > -100:
            deltax = -100
        deltay = y1 - y0
        a = - deltay / float(deltax*deltax)
        b = 2 * deltay / float(deltax)
        for x in range(self.x, -self.ico.w, -13):
            x1 = x - x0
            self.move(x, y0 + int((a*x1+b)*x1))
            yield None
            for s in self.touching(10):
                if isinstance(s, Monster):
                    s.argh(poplist)
                elif isinstance(s, Bubble):
                    s.pop(poplist)
        self.kill()

class Fish2(RandomBonus):
    points = 3000
    nimage = Bonuses.fish2
    def taken1(self, dragons):
        if dragons:
            Megalightning(self.x, self.y, random.choice(dragons))

class Sheep(RandomBonus):
    nimage = 'sheep-sm'
    points = 800
    def __init__(self, x, y):
        RandomBonus.__init__(self, x, y)
        if boards.curboard.bonuslevel:
            self.kill()
    def taken1(self, dragons):
        self.points0 = {}
        for p in BubPlayer.PlayerList:
            if p.isplaying():
                self.points0[p] = p.points
        BubPlayer.LeaveBonus = self.boardleave()

    def boardleave(self):
        gamesrv.set_musics([], [])
        images.Snd.Yippee.play()
        slist = []
        ico = images.sprget('sheep-big')
        for d in BubPlayer.DragonList[:]:
            dx = (d.ico.w - ico.w) // 2
            dy = (d.ico.h - ico.h) // 2
            s = ActiveSprite(ico, d.x + dx, d.y + dy)
            s.gen.append(s.parabolic([d.dir, -2.0]))
            slist.append(s)
            d.kill()
        delta = {}
        for p in BubPlayer.PlayerList:
            if p.isplaying():
                delta[p] = (self.points0.get(p, 0) - p.points) // 10
        vy = 0
        for i in range(20):
            for p, dp in delta.items():
                p.givepoints(dp)
            for j in range(4):
                for s in slist:
                    s.action()
                yield 1
        while slist:
            slist = [s for s in slist if s.y < boards.bheight]
            for s in slist:
                s.action()
            yield 1

Classes = [c for c in globals().values()
           if type(c)==type(RandomBonus) and issubclass(c, RandomBonus)]
Classes.remove(RandomBonus)
Classes.remove(TemporaryBonus)
Cheat = [] #[Book, Door, Bomb, Ham]
#Classes = [Fruits]  # CHEAT

AllOutcomes = ([(c,) for c in Classes if c is not Fruits] +
               2 * [(MonsterBonus, lvl)
                    for lvl in range(len(Bonuses.monster_bonuses))])

for c in Classes:
    assert (getattr(c, 'points', 0) or 100) in GreenAndBlue.points[0], c

def chooseground(tries=15):
    for i in range(tries):
        x0 = random.randint(2, boards.width-4)
        y0 = random.randint(1, boards.height-3)
        if (' ' == bget(x0,y0+1) == bget(x0+1,y0+1) and
            '#' == bget(x0,y0+2) == bget(x0+1,y0+2)):
            x0 *= CELL
            y0 *= CELL
            for d in BubPlayer.DragonList:
                if abs(d.x-x0) < 3*CELL and abs(d.y-y0) < 3*CELL:
                    break
            else:
                return x0, y0
    else:
        return None, None

def newbonus():
    others = [s for s in images.ActiveSprites if isinstance(s, RandomBonus)]
    if others:
        return
    x, y = chooseground()
    if x is None:
        return
    cls = random.choice(Classes)
    cls(x, y)

##def newbonus():
##    others = [s for s in images.ActiveSprites if isinstance(s, RandomBonus)]
##    if others:
##        return
##    for cls in Classes:
##        x, y = chooseground(200)
##        if x is not None:
##            cls(x, y)

def cheatnew():
    if Cheat:
        x, y = chooseground()
        if x is None:
            return
        cls = random.choice(Cheat)
        cls(x, y)
