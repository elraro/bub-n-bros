from __future__ import generators
import random, math, time
import gamesrv
import images
import boards
import bubbles
from boards import *
from images import ActiveSprite
from mnstrmap import GreenAndBlue, LetterBubbles, PlayerBubbles
from mnstrmap import DigitsMisc

KEEPALIVE = 5*60   # seconds
CheatDontDie = 0


class Dragon(ActiveSprite):
    priority = 1
    mdef = PlayerBubbles
    fly_counter = 0
    glueddown = None

    DCAP = {
        'hspeed': 1,
        'firerate': 2,
        'shootthrust': 8.0,
        'infinite_shield': 1,
        'shield': 50,
        'gravity': 0.21,
        'bubbledelay': 0,
        'shootbubbles': (),
        'pinball': 0,
        'nojump': 0,
        'autofire': 0,
        'ring': 0,
        'hotstuff': 0,
        'left2right': 1,
        'slippy': 0,
        'vslippy': 0.0,
        'lookforward': 1,
        'fly': 0,
        'flower': 1,
        'overlayglasses': 0,
        'carrying': (),
        }
    SAVE_CAP = {'hspeed': 1,
                'firerate': 2,
                'shootthrust': 8.0 / 1.5,
                'flower': 0}
    
    def __init__(self, bubber, x, y, dir, dcap=DCAP):
        self.bubber = bubber
        self.dir = dir
        ActiveSprite.__init__(self, bubber.icons[0, dir], x, y)
        self.fire = 0
        self.up = 0.0
        self.watermoveable = 0
        self.dcap = dcap.copy()
        self.dcap.update(self.bubber.pcap)
        BubPlayer.DragonList.append(self)
        self.gen.append(self.normal_movements())
        self.overlaysprite = None
        self.overlayyoffset = 4
        self.hatsprite = None
        self.hatangle = 1
        self.isdying = 0

    def kill(self):
        try:
            BubPlayer.DragonList.remove(self)
        except ValueError:
            pass
        try:
            self.bubber.dragons.remove(self)
        except ValueError:
            pass
        ActiveSprite.kill(self)
        if self.hatsprite is not None:
            if self.hatsprite.alive:
                self.hatsprite.kill()
            self.hatsprite = None

    def die(self):
        if (self in BubPlayer.DragonList and not self.dcap['shield']
            and not CheatDontDie):
            BubPlayer.DragonList.remove(self)
            self.gen = [self.dying()]
            self.play(images.Snd.Die)
            #wasting = boards.curboard.wastingplay
            #if wasting is not None:
            #    wasting[self.bubber] = len(wasting)

    def dying(self, can_loose_letter=1):
        self.isdying = 1
        if self.hatsprite is not None:
            if self.hatsprite.alive:
                dxy = [3*self.dir, -7]
                self.hatsprite.gen = [self.hatsprite.parabolic(dxy)]
            self.hatsprite = None
        lst = [bonus for timeout, bonus in self.dcap['carrying']
               if hasattr(bonus, 'buildoutcome')]
               #if random.random() > 0.2]
        if lst:
            # loose some bonuses
            from bonuses import BonusMaker
            for bonus in lst:
                self.bubber.givepoints(-bonus.points)
                BonusMaker(self.x, self.y, [bonus.nimage],
                           outcome=bonus.buildoutcome())
        elif self.bubber.letters and random.random() > 0.59 and can_loose_letter:
            # loose a letter
            lst = range(6)
            random.shuffle(lst)
            for l in lst:
                lettername = bubbles.extend_name(l)
                if lettername in self.bubber.letters:
                    s = self.bubber.letters[lettername]
                    del self.bubber.letters[lettername]
                    if isinstance(s, ActiveSprite):
                        s.kill()
                    scoreboard()
                    s = bubbles.LetterBubble(self.bubber.pn, l)
                    s.move(self.x, self.y)
                    break
        for i in range(2, 32):
            mode = 5 + ((i>>1) & 3)
            self.seticon(self.bubber.icons[mode, self.dir])
            yield None
        self.kill()
        if not self.bubber.dragons:
            self.bubber.bubberdie()
        #    self.bubber.badpoints = self.bubber.points // 3

    def killing(self):
        self.kill()
        if 0:
            yield None

    def carrybonus(self, bonus, timeout=500):
        timeout += BubPlayer.FrameCounter
        lst = list(self.dcap['carrying'])
        lst.append((timeout, bonus))
        lst.sort()
        self.dcap['carrying'] = lst

    def listcarrybonuses(self):
        return [bonus for timeout, bonus in self.dcap['carrying']]

    def moebius(self):
        self.dir = -self.dir
        self.dcap['left2right'] *= -1

    def normal_movements(self):
        yfp = 0.0
        hfp = 0
        angryticks = 0
        mytime = 0
        while 1:
            self.poplist = [self]
            carrying = self.dcap['carrying']
            while carrying and carrying[0][0] < BubPlayer.FrameCounter:
                timeout, bonus = carrying.pop(0)
                if bonus.endaction:
                    bonus.endaction(self)
                del bonus

            bubber = self.bubber
            wannafire = bubber.key_fire
            wannajump = bubber.key_jump
            wannago = bubber.wannago(self.dcap)
            bottom_up = self.bottom_up()

            if self.dcap['autofire']:
                wannafire = 1
            if self.dcap['pinball']:
                wannajump = 1
                if self.dcap['pinball'] > 1:
                    if self.up:
                        self.up *= 0.982 ** self.dcap['pinball']
            if self.dcap['hotstuff']:
                if not wannago:
                    if self.dir * (random.random()-0.07) < 0:
                        wannago = -1
                    else:
                        wannago = 1
                wannafire = 1
                if self.fire > 11:
                    self.fire = 0
            if wannago:
                self.dir = wannago * self.dcap['lookforward']
            if self.x & 1:
                self.step(self.dir, 0)
            if self.dcap['slippy']:
                vx = self.dcap['vslippy']
                if wannago:
                    vx += wannago * 0.05
                else:
                    vx *= 0.95
                if vx < 0.0:
                    wannago = -1
                else:
                    wannago = 1
                self.dcap['vslippy'] = vx
                mytime = (mytime+self.dcap['lookforward']) % 12
                hfp += abs(vx)
            else:
                hfp += self.dcap['hspeed']

            if self.glueddown:
                if wannajump or not self.dcap['nojump']:
                    del self.glueddown
                else:
                    # glued gliding movements
                    self.step(self.x & 1, self.y & 1)
                    if wannago:
                        mytime = (mytime+self.dcap['lookforward']) % 12
                    else:
                        hfp = 0
                    while hfp > 0 and self.glueddown:
                        gx, gy = self.glueddown
                        dx = wannago*gy
                        dy = -wannago*gx
                        x0 = (self.x + gx + dx) // CELL + 1
                        y0 = (self.y + gy + dy) // CELL + 1
                        if ' ' == bget(x0+dx, y0+dy) == bget(x0+dx-gx, y0+dy-gy):
                            self.step(2*dx, 2*dy)
                            # detached from this wall?
                            x1 = (self.x + gx + dx) // CELL + 1
                            y1 = (self.y + gy + dy) // CELL + 1
                            if (' ' == bget(x1-dx+gx, y1-dy+gy)
                                    == bget(x0   +gx, y0   +gy)
                                    == bget(x0+dx+gx, y0+dy+gy)):
                                if bget(x0-dx+gx, y0-dy+gy) != ' ':
                                    # rotate around the corner
                                    self.glueddown = -dx, -dy
                                    self.step(2*gx, 2*gy)
                                else:
                                    del self.glueddown
                        elif bget(x0-gx, y0-gy) == ' ':
                            # attach to the wall into which we are running
                            if (self.x*dx | self.y*dy) % CELL != 0:
                                if ((((self.x-2*dx)*dx | (self.y-2*dy)*dy) &
                                     ((self.x-4*dx)*dx | (self.y-4*dy)*dy))
                                    % CELL == 0):
                                    self.step(-2*dx, -2*dy)
                                else:
                                    del self.glueddown
                            else:
                                self.glueddown = dx, dy
                        else:
                            del self.glueddown
                        self.vertical_warp()
                        hfp -= 0.82   # slightly faster than usual
            # normal left or right movements
            while hfp > 0:
                hfp -= 1
                dir = 0
                if wannago == -1:
                    x0 = (self.x+1)//CELL
                    y0 = (self.y+4) // CELL + 1 - bottom_up
                    y0bis = (self.y+CELL-1) // CELL + 1 - bottom_up
                    if bget(x0,y0) == ' ' == bget(x0,y0bis):
                        dir = -1
                elif wannago == 1:
                    x0 = (self.x-3)//CELL + 2
                    y0 = self.y // CELL + 1 - bottom_up
                    y0bis = (self.y+CELL-1) // CELL + 1 - bottom_up
                    if bget(x0,y0) == ' ' == bget(x0,y0bis):
                        dir = +1
                self.step(2*dir, 0)
                if dir:
                    mytime = (mytime+self.dcap['lookforward']) % 12
                else:
                    self.dcap['vslippy'] *= -0.6666
            onbubble = 0
            if not self.dcap['infinite_shield']:
                touching = images.touching(self.x+1, self.y+1, 30, 30)
                touching.reverse()
                for s in touching:
                    if s.touched(self):
                        onbubble = max(onbubble, getattr(s,'solidbubble',0)+1)
            elif bubber.key_left or bubber.key_right or bubber.key_jump or bubber.key_fire:
                self.dcap['infinite_shield'] = 0

            dir = self.dir
            imgtransform = 'vflip' * bottom_up
            if self.glueddown:
                # glued movements: done above
                mode = mytime // 6 * 2
                imgtransform = {
                    (0, 1): '',
                    (0,-1): 'vflip',
                    (-1,0): 'cw',
                    ( 1,0): 'ccw',
                    }[self.glueddown]
                if self.glueddown == (0, -1):
                    dir = -self.dir
            elif self.up:
                # going up
                mode = 9
                self.up -= self.dcap['gravity']
                if (self.up,-self.up)[bottom_up] < 4.0:
                    self.up = 0.0
                    #self.key_jump = 0
                    mode = 10
                else:
                    ny = self.y + yfp - self.up
                    self.move(self.x, int(ny))
                    yfp = ny - self.y
                    if ny < -2*CELL or ny >= boards.bheight:
                        self.vertical_warp()
            else:
                # going down or staying on ground
                ground = (onground,underground)[bottom_up](self.x, self.y)
                if ground or onbubble>1 or (
                    wannajump and onbubble and not self.dcap['nojump']):
                    if self.dcap['nojump']:
                        mode = 0
                        self.glueddown = (0, (1,-1)[bottom_up])
                    elif wannajump:
                        self.play(images.Snd.Jump)
                        yfp = 0.0
                        self.up = (7.5,-7.5)[bottom_up]
                        mode = 9
                    else:
                        mode = mytime // 4
                else:
                    mode = 10
                    if self.dcap['fly']:
                        self.fly_counter += 1
                        if self.fly_counter < self.dcap['fly']:
                            ny = self.y
                        else:
                            del self.fly_counter
                            ny = self.y+(1,-1)[bottom_up]
                    else:
                        ny = (self.y+(4,-1)[bottom_up]) & ~3
                    nx = self.x
                    if nx < 32:
                        nx += 2
                    elif nx > boards.bwidth - 64:
                        nx -= 2
                    self.move(nx, ny)
                    if ny >= boards.bheight or ny < -2*CELL:
                        self.vertical_warp()

            if wannafire and not self.fire:
                self.firenow()
            self.hatangle = 1
            if self.fire:
                if self.fire <= 5:
                    mode = 3
                    self.hatangle = 2
                elif self.fire <= 10:
                    mode = 4
                    self.hatangle = 3
                self.fire += 1
                if self.fire >= 64 // self.dcap['firerate']:
                    self.fire = 0

            s = self.dcap['shield']
            if s:
                if self.dcap['infinite_shield'] and s < 20:
                    s += 4
                s -= 1
                if self.dcap['overlayglasses']:
                    self.overlayyoffset = {3: 2, 4: 0,
                                           9: 3, 10: 5}.get(mode, 4)
                elif s & 2:
                    mode = 11
                self.dcap['shield'] = s
            if self.dcap['ring']:# and random.random() > 0.1:
                if self.dcap['ring'] > 1:
                    mode = 12
                else:
                    mode = 11
            try:
                icons = self.bubber.transformedicons[imgtransform]
            except KeyError:
                icons = self.bubber.transformedicons[imgtransform] = {}
                self.bubber.loadicons(imgtransform)
            self.seticon(icons[mode, dir])

            self.watermoveable = not wannajump
            yield None
            
            if self.angry:
                if angryticks == 0:
                    s = ActiveSprite(icons[11, self.dir], self.x, self.y)
                    s.gen.append(s.die([None], speed=10))
                    angryticks = 6
                angryticks -= 1
            #if BubPlayer.Moebius and BubPlayer.FrameCounter % 5 == 0:
            #    s = ActiveSprite(icons[11, -self.dir],
            #                     boards.bwidth - 2*CELL - self.x, self.y)
            #    s.gen.append(s.die([None], speed=2))

    def to_front(self):
        ActiveSprite.to_front(self)
        if self.dcap['overlayglasses']:
            ico = images.sprget(('glasses', self.dir))
            y = self.y + self.overlayyoffset
            if self.overlaysprite is None or not self.overlaysprite.alive:
                self.overlaysprite = images.ActiveSprite(ico, self.x, y)
            else:
                self.overlaysprite.to_front()
                self.overlaysprite.move(self.x, y, ico)
            self.overlaysprite.gen = [self.overlaysprite.die([None])]

    def bottom_up(self):
        return self.dcap['gravity'] < 0.0

    def watermove(self, x, y):
        # for WaterCell.flooding()
        if self in BubPlayer.DragonList and self.watermoveable:
            self.watermoveable = 0
            self.move(x, y)
            self.up = 0.0
            if self.dcap['shield'] < 6:
                self.dcap['shield'] = 6
            if self.fire <= 10:
                self.fire = 11

    def become_monster(self, clsname, big=0):
        if self in BubPlayer.DragonList:
            BubPlayer.DragonList.remove(self)
            
            import monsters, mnstrmap
            mcls = getattr(monsters, clsname)
            mdef = getattr(mnstrmap, clsname)
            m = mcls(mdef, self.x, self.y, self.dir, in_list=self.bubber.dragons)
            m.become_monster(self.bubber, self.dcap, big)
            self.gen = [self.killing()]

    def become_bubblingeyes(self, bubble):
        if self in BubPlayer.DragonList:
            self.bubber.emotic(self, 4)
            BubPlayer.DragonList.remove(self)

            import bubbles
            bubble.to_front()
            m = bubbles.BubblingEyes(self.bubber, self.dcap, bubble)
            self.bubber.dragons.append(m)
            self.gen = [self.killing()]
            return 1
        else:
            return 0

    def firenow(self):
        self.fire = 1
        #if boards.curboard.wastingplay is None:
        shootbubbles = self.dcap['shootbubbles']
        special_bubbles = shootbubbles and shootbubbles.pop()
        N = self.dcap['flower']
        if N == 1:
            angles = [0]
        elif N > 1:
            angles = [i*(2.0*math.pi/N) for i in range(N)]
            self.dcap['flower'] = N*2//3
        else:  # N == 0 for triple fire
            angles = [0, -0.19, 0.19]
        dir = self.dir
        x = self.x
        if self.glueddown:
            gx, gy = self.glueddown
            dir = dir*gy
            if not dir:
                dir = 1
                delta = self.dir*gx * math.pi/2
                angles = [angle-delta for angle in angles]
                x -= 16
        for angle in angles:
            bubbles.DragonBubble(self, x + 4*dir, self.y, dir,
                                 special_bubbles, angle)
        #else:
        #    from monsters import DragonShot
        #    DragonShot(self)

class BubPlayer(gamesrv.Player):
    # global state
    FrameCounter = 0
    PlayerList = []
    DragonList = []
    MonsterList = []
    LimitScore = 0
    LimitScoreColor = None
    LimitTime = None
    #HighScore = 0
    #HighScoreColor = None

    INIT_BOARD_CAP = {
        #'LatestLetsGo': -999,
        'BubblesBecome': None,
        'MegaBonus': None,
        'BaseFrametime': 1.0,
        'LeaveBonus': None,
        'Moebius': 0,
        'OverridePlayerIcon': None,
        }
    TRANSIENT_DATA = ('_client', 'key_left', 'key_right',
                      'key_jump', 'key_fire', 'pn', 'nameicons',
                      'icons', 'transformedicons',
                      'standardplayericon', 'iconnames')

    def __init__(self, n):
        self.pn = n
        self.icons = {}
        self.transformedicons = {'': self.icons}
        self.standardplayericon = images.sprget(GreenAndBlue.players[n][3])
        self.iconnames = {
            (0, -1): GreenAndBlue.players[n][0],  # walk
            (0, +1): GreenAndBlue.players[n][3],
            (1, -1): GreenAndBlue.players[n][1],
            (1, +1): GreenAndBlue.players[n][4],
            (2, -1): GreenAndBlue.players[n][2],
            (2, +1): GreenAndBlue.players[n][5],
            (3, -1): GreenAndBlue.players[n][6],  # lancer de bulle
            (3, +1): GreenAndBlue.players[n][8],
            (4, -1): GreenAndBlue.players[n][7],
            (4, +1): GreenAndBlue.players[n][9],
            (5, -1): GreenAndBlue.players[n][0],  # mort
            (5, +1): GreenAndBlue.players[n][0],
            (6, -1): GreenAndBlue.players[n][11],
            (6, +1): GreenAndBlue.players[n][10],
            (7, -1): GreenAndBlue.players[n][12],
            (7, +1): GreenAndBlue.players[n][12],
            (8, -1): GreenAndBlue.players[n][10],
            (8, +1): GreenAndBlue.players[n][11],
            (9, -1): GreenAndBlue.jumping_players[n][2],  # saut, montant
            (9, +1): GreenAndBlue.jumping_players[n][3],
            (10,-1): GreenAndBlue.jumping_players[n][0],  # saut, descend
            (10,+1): GreenAndBlue.jumping_players[n][1],
            (11,-1): 'shield-left',    # shielded
            (11,+1): 'shield-right',
            (12,-1): 'black',          # totally invisible
            (12,+1): 'black',
            }
        self.nameicons = []
        self.team = -1
        self.reset()

    def reset(self):
        self.letters = {}
        #self.bonbons = 0
        self.points = 0
        self.nextextralife = gamesrv.game.extralife
        self.lives = boards.get_lives()
        #self.badpoints = 0
        self.pcap = {}
        self.dragons = []
        self.keepalive = None
        self.stats = {'bubble': 0, 'die': 0}

    def loadicons(self, flip):
        icons = self.transformedicons[flip]
        for key, value in self.iconnames.items():
            icons[key] = images.sprget((flip, value))

    def setplayername(self, name):
        name = name.strip()
        for t in [0, 1]:
            if name.endswith('(%d)' % (t+1)):
                self.team = t
                name = name[:-3].strip()
                #print "New player in team", t, "with name", name
                break
        else:
            self.team = -1
            #print "New player with no team:", name
        icons = [images.sprcharacterget(c) for c in name]
        self.nameicons = [ico for ico in icons if ico is not None][:16]
        self.nameicons.reverse()
        scoreboard()

    def playerjoin(self):
        n = self.pn
        if not self.icons:
            self.loadicons(flip='')
        self.keepalive = None
        if self.points or self.letters:
            print 'New player continues at position #%d.' % n
        else:
            print 'New player is at position #%d.' % n
            self.reset()
        self.key_left  = 0
        self.key_right = 0
        self.key_jump  = 0
        self.key_fire  = 0
        players = [p for p in BubPlayer.PlayerList
                   if p.isplaying() and p is not self]
        self.enterboard(players)
        scoreboard()
        #if BubPlayer.LatestLetsGo < BubPlayer.FrameCounter - 30:
        images.Snd.LetsGo.play()
        #BubPlayer.LatestLetsGo = BubPlayer.FrameCounter

    def playerleaves(self):
        print 'Closing position #%d.' % self.pn
        self.savecaps()
        self.zarkoff()
        self.keepalive = time.time() + KEEPALIVE
        scoreboard()

    def sameteam(self, other):
        return self.team != -1 and self.team == other.team

    def enterboard(self, players):
        players = [p for p in players if not p.sameteam(self)]
        leftplayers = [p for p in players if p.start_left]
        rightplayers = [p for p in players if not p.start_left]
        self.start_left = (len(leftplayers) + random.random() <
                           len(rightplayers) + random.random())

    def savecaps(self):
        dragons = self.dragons
        if dragons:
            for key, minimum in Dragon.SAVE_CAP.items():
                self.pcap[key] = max(minimum,
                                     max([d.dcap[key] for d in dragons]))

    def zarkoff(self):
        for d in self.dragons[:]:
            d.kill()
        del self.dragons[:]

    def zarkon(self):
        if self.key_left + self.key_right >= 1999997:
            for dragon in self.dragons:
                self.emotic(dragon, 6)
            self.key_left = self.key_right = 900000
        if self.key_left:  self.key_left  -= 1
        if self.key_right: self.key_right -= 1
        if self.key_jump:  self.key_jump  -= 1
        if self.key_fire:  self.key_fire  -= 1
        #if self.badpoints and not (self.FrameCounter & 7):
        #    percent = (int(self.points*0.0000333)+1) * 100
        #    decr = min(self.badpoints, percent)
        #    self.badpoints -= decr
        #    self.givepoints(-decr)
        if boards.curboard and not self.dragons and self.lives != 0:
            #wasting = boards.curboard.wastingplay
            #if wasting is not None and self in wasting:
            #    return
            if self.start_left:
                x0 = 3*CELL
                dir = 1
            else:
                x0 = boards.bwidth - 5*CELL
                dir = -1
            y = boards.bheight - 3*CELL
            for x in [x0, x0+4*dir, x0+8*dir, x0+12*dir, x0+16*dir,
                      x0-4*dir, x0-8*dir, x0]:
                if onground(x,y):
                    for d in BubPlayer.DragonList:
                        if d.y == y and abs(d.x-x) <= 5:
                            break
                    else:
                        break
            self.dragons.append(Dragon(self, x, y, dir))
            self.pcap = {}

    def kLeft(self):
        if self.key_left <= 1:
            self.key_left = 1000000
    def kmLeft(self):
        self.key_left = (self.key_left == 1000000)
    def kRight(self):
        if self.key_right <= 1:
            self.key_right = 1000000
    def kmRight(self):
        self.key_right = (self.key_right == 1000000)
    def kJump(self):
        if self.key_jump <= 1:
            self.key_jump = 1000000
    def kmJump(self):
        self.key_jump = (self.key_jump == 1000000)
    def kFire(self):
        if self.key_fire <= 1:
            self.key_fire = 1000000
    def kmFire(self):
        self.key_fire = (self.key_fire == 1000000)

    def bubberdie(self):
        self.stats['die'] += 1
        if self.lives is not None and self.lives > 0:
            self.lives -= 1
            scoreboard()

    def wannago(self, dcap):
        return dcap['left2right'] * cmp(self.key_right, self.key_left)

    def givepoints(self, points):
        self.points += points
        if self.points < 0:
            self.points = 0
        while self.points >= self.nextextralife:
            if self.lives is not None and self.lives > 0:
                if self.dragons:
                    dragon = random.choice(self.dragons)
                    dragon.play(images.Snd.Extralife)
                else:
                    images.Snd.Extralife.play()
                self.lives += 1
            self.nextextralife += gamesrv.game.extralife
        if self.LimitScoreColor is not None and self.points >= self.LimitScore:
            boards.replace_boardgen(boards.game_over(), 1)
        #if self.points > BubPlayer.HighScore:
        #    BubPlayer.HighScore = self.points
        #    BubPlayer.HighScoreColor = self.pn
        scoreboard()

    def giveletter(self, l, promize=100000):
        
        #logf = open('log', 'a')
        #print >> logf 'giveletter %d:' % self.pn, l
        #logf.close()
        
        lettername = bubbles.extend_name(l)
        if lettername not in self.letters:
            self.letters[lettername] = 1
##            nimage = getattr(LetterBubbles, lettername)
##            x0, y0 = self.infocoords()
##            s = images.ActiveSprite(images.sprget(nimage[1]), x0+l*(CELL-1), y0 - 3*CELL)
##            s.gen.append(s.cyclic([nimage[1], nimage[2], nimage[1], nimage[0]], 7))
            scoreboard()
            if len(self.letters) == 6:
                import monsters
                monsters.argh_em_all()
                import bonuses
                if self.dragons:
                    for i in range(3):
                        dragon = random.choice(self.dragons)
                        bonuses.starexplosion(dragon.x, dragon.y, 1)
                    for lettername in self.letters:
                        dragon = random.choice(self.dragons)
                        nimages = getattr(LetterBubbles, lettername)
                        bonuses.Parabolic2(dragon.x, dragon.y, nimages)
                    dragon = random.choice(self.dragons)
                    dragon.play(images.Snd.Extralife)
                music = [images.music_old]
                boards.replace_boardgen(boards.last_monster_killed(460, music))
                self.givepoints(promize)

    def emotic(self, dragon, strenght):
        bottom_up = hasattr(dragon, 'bottom_up') and dragon.bottom_up()
        vshift = getattr(dragon, 'up', 0.0)
        for i in range(7):
            angle = math.pi/6 * i
            dx, dy = -math.cos(angle), -math.sin(angle)
            nx = random.randrange(3,12)*dx
            ny = random.randrange(3,9)*dy - 12
            if bottom_up:
                dy = -dy
                ny = -ny
            e = ActiveSprite(images.sprget(('vflip'*bottom_up, ('emotic', i))),
                             int(dragon.x + 8 + nx),
                             int(dragon.y + 8 + ny - vshift))
            e.gen.append(e.straightline((3.3+random.random())*dx, (2.3+random.random())*dy))
            e.gen.append(e.die([None], strenght))


def upgrade(p):
    p.__class__ = BubPlayer
    p.key_left  = 0
    p.key_right = 0
    p.key_jump  = 0
    p.key_fire  = 0
    p.dragons = []


def xyiconumber(digits, x, y, pts, lst, width=7):
    if pts >= 10**width:
        pts = 10**width-1
    for l in range(width):
        ico = images.sprget(digits[pts % 10])
        lst.append((x + (ico.w+1)*(width-1-l), y, ico))
        pts = pts//10
        if not pts:
            break
    return lst[-1][0]

def scoreboard(reset=0, inplace=0):
    endgame = 1
    if reset:
        for p in BubPlayer.PlayerList:
            if inplace:
                for s in p.letters.values():
                    if isinstance(s, ActiveSprite):
                        s.kill()
            if len(p.letters) == 6:
                p.letters.clear()
            for key in p.letters:
                p.letters[key] = 2
    brd = boards.curboard
    if not brd or not gamesrv.sprites_by_n:
        return
    lst = []
    bubblesshown = {}
    plist = []
    teamslist = [[], []]
    teamspoints = [0, 0]
    for p in BubPlayer.PlayerList:
        if p.isplaying():
            if p.lives != 0:
                endgame = 0
        else:
            if not p.keepalive:
                continue
            if p.keepalive < time.time():
                p.reset()
                continue
        if p.team == -1:
            plist.append((p.points, p, None))
        else:
            teamslist[p.team].append((p.points,p))
            teamspoints[p.team] += p.points
    teamslist[0].sort()
    teamslist[1].sort()
    plist.append((teamspoints[0], None, teamslist[0]))
    plist.append((teamspoints[1], None, teamslist[1]))
    plist.sort()
    x0 = boards.bwidth
    y0 = boards.bheight
    for score, p, t in plist:
        if p:
            if p.lives == 0:
                ico = images.sprget(GreenAndBlue.gameover[p.pn][0])
            elif p.icons:
                if p.isplaying():
                    mode = 0
                else:
                    mode = 11
                ico = BubPlayer.OverridePlayerIcon or p.icons[mode, -1]
            lst.append((x0+9*CELL-ico.w, y0-ico.h, ico))
            #if boards.curboard.wastingplay is None:
            for l in range(6):
                name = bubbles.extend_name(l)
                if name in p.letters:
                    x, y = x0+l*(CELL-1), y0-3*CELL
                    imglist = getattr(LetterBubbles, name)
                    ico = images.sprget(imglist[1])
                    if gamesrv.game.End in (0, 1):
                        s = p.letters[name]
                        if (isinstance(s, ActiveSprite) and
                            BubPlayer.FrameCounter <= s.timeout):
                            s.move(x, y)
                            bubblesshown[s] = 1
                            continue
                        if s == 1:
                            s = ActiveSprite(ico, x, y)
                            s.setimages(s.cyclic([imglist[0], imglist[1],
                                                imglist[2], imglist[1]]))
                            s.timeout = BubPlayer.FrameCounter + 500
                            p.letters[name] = s
                            bubblesshown[s] = 1
                            continue
                    lst.append((x, y, ico))
    ##        else:
    ##            ico = images.sprget(Bonuses.blue_sugar)
    ##            lst.append((x0+12, y0-3*CELL-8, ico))
    ##            xyiconumber(DigitsMisc.digits_white, x0-19, y0-3*CELL+5,
    ##                        p.bonbons, lst)
            xyiconumber(GreenAndBlue.digits[p.pn], x0+2, y0-18, score, lst)
            if p.lives is not None and p.lives > 0:
                xyiconumber(DigitsMisc.digits_white, x0+7*CELL, y0-18,
                            p.lives, lst, width=2)
            x = x0+13*HALFCELL
            for ico in p.nameicons:
                x -= 7
                lst.append((x, y0-35, ico))
            y0 -= 7*HALFCELL
        else: # Team
            for pscore, p in t:
                if p.lives == 0:
                    ico = images.sprget(GreenAndBlue.gameover[p.pn][0])
                elif p.icons:
                    if p.isplaying():
                        mode = 0
                    else:
                        mode = 11
                    ico = BubPlayer.OverridePlayerIcon or p.icons[mode, -1]
                lst.append((x0+9*CELL-ico.w, y0-ico.h, ico))
                for l in range(6):
                    name = bubbles.extend_name(l)
                    if name in p.letters:
                        x, y = x0+l*(CELL-1), y0-2*CELL
                        imglist = getattr(LetterBubbles, name)
                        ico = images.sprget(imglist[1])
                        if gamesrv.game.End in (0, 1):
                            s = p.letters[name]
                            if (isinstance(s, ActiveSprite) and
                                BubPlayer.FrameCounter <= s.timeout):
                                s.move(x, y)
                                bubblesshown[s] = 1
                                continue
                            if s == 1:
                                s = ActiveSprite(ico, x, y)
                                s.setimages(s.cyclic([imglist[0], imglist[1],
                                                    imglist[2], imglist[1]]))
                                s.timeout = BubPlayer.FrameCounter + 500
                                p.letters[name] = s
                                bubblesshown[s] = 1
                                continue
                        lst.append((x, y, ico))
                x = x0+13*HALFCELL
                for ico in p.nameicons:
                    x -= 7
                    lst.append((x, y0-19, ico))
                y0 -= 4*HALFCELL
            if t != []:
                xyiconumber(GreenAndBlue.digits[t[-1][1].pn], x0+2, y0-18, score, lst)
                ico = images.sprget(('hat', p.team, -1, 1))
                lst.append((x0+9*CELL-ico.w, y0-ico.h+16, ico))
                y0 -= 5*HALFCELL
    for p in BubPlayer.PlayerList:
        for name, s in p.letters.items():
            if isinstance(s, ActiveSprite) and s not in bubblesshown:
                p.letters[name] = 2
                s.kill()
    compressable = len(lst)
    ymin = 0
    #if BubPlayer.HighScoreColor is not None:
    #    x = xyiconumber(GreenAndBlue.digits[BubPlayer.HighScoreColor],
    #                    x0+2*CELL, HALFCELL, BubPlayer.HighScore, lst)
    #    ico = images.sprget(GreenAndBlue.players[BubPlayer.HighScoreColor][3])
    #    lst.append((x-5*HALFCELL, 1, ico))
    if BubPlayer.LimitScoreColor is not None:
        xyiconumber(GreenAndBlue.digits[BubPlayer.LimitScoreColor],
                    x0+2*CELL, HALFCELL, BubPlayer.LimitScore, lst)
    if BubPlayer.LimitTime is not None:
        seconds = int(BubPlayer.LimitTime)
        xyiconumber(DigitsMisc.digits_white, x0+2*CELL, HALFCELL,
                    seconds // 60, lst, width=3)
        ico = images.sprget('colon')
        lst.append((x0+5*CELL-1, HALFCELL+1, ico))
        seconds = seconds % 60
        ico = images.sprget(DigitsMisc.digits_white[seconds // 10])
        lst.append((x0+6*CELL, HALFCELL, ico))
        ico = images.sprget(DigitsMisc.digits_white[seconds % 10])
        lst.append((x0+6*CELL+ico.w, HALFCELL, ico))
        ymin = HALFCELL + ico.h
    if not brd.bonuslevel:
        xyiconumber(DigitsMisc.digits_white, 2, 2, brd.num+1, lst, width=2)

    # compress the scoreboard vertically if it doesn't fit
    ymin += HALFCELL
    if y0 < ymin:
        factor = float(boards.bheight-ymin) / (boards.bheight-y0)
        shift = ymin - y0*factor + 0.5
        for i in range(compressable):
            x, y, ico = lst[i]
            lst[i] = x, int((y+ico.h)*factor+shift)-ico.h, ico

    brd.writesprites('scoreboard', lst)

    if gamesrv.game.End in (0, 1):
        gamesrv.game.End = endgame


# initialize global board data
BubPlayer.__dict__.update(BubPlayer.INIT_BOARD_CAP)
