from __future__ import generators
import random
import gamesrv
import images
import boards
import bubbles
from boards import *
from images import ActiveSprite
from mnstrmap import GreenAndBlue, LetterBubbles, PlayerBubbles
from mnstrmap import DigitsMisc

MAX = 7
CheatDontDie = 0
ExtraLifeEvery = 50000

KeyJustPressed  = 7
KeyPressed      = 6
KeyJustClicked  = 5
KeyOff          = 0


class Dragon(ActiveSprite):
    priority = 1
    mdef = PlayerBubbles

    DCAP = {
        'hspeed': 1,
        'firerate': 2,
        'shootthrust': 8.0,
        'infinite_shield': 1,
        'shield': 50,
        'gravity': 0.21,
        'bubbledelay': 800,
        'shootbubbles': (),
        'pinball': 0,
        'autofire': 0,
        'ring': 0,
        'hotstuff': 0,
        'left2right': 1,
        'slippy': 0,
        'vslippy': 0.0,
        'lookforward': 1,
        'fly': 0,
        'carrying': (),
        }
    SAVE_CAP = ['hspeed', 'firerate', 'shootthrust']
    
    def __init__(self, bubber, x, y, dir, dcap=DCAP):
        self.bubber = bubber
        self.dir = dir
        ActiveSprite.__init__(self, bubber.icons[0, dir], x, y)
        self.mytime = 0
        self.fire = 0
        self.up = 0.0
        self.watermoveable = 0
        self.dcap = dcap.copy()
        self.dcap.update(self.bubber.pcap)
        BubPlayer.DragonList.append(self)
        self.gen.append(self.normal_movements())

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

    def die(self):
        if (self in BubPlayer.DragonList and not self.dcap['shield']
            and not CheatDontDie):
            BubPlayer.DragonList.remove(self)
            self.gen = [self.dying()]
            self.play(images.Snd.Die)
            #wasting = boards.curboard.wastingplay
            #if wasting is not None:
            #    wasting[self.bubber] = len(wasting)

    def dying(self):
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
        elif self.bubber.letters and random.random() > 0.59:
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

    def normal_movements(self):
        yfp = 0.0
        hfp = 0
        angryticks = 0
        while 1:
            self.poplist = [self]
            carrying = self.dcap['carrying']
            while carrying and carrying[0][0] < BubPlayer.FrameCounter:
                timeout, bonus = carrying.pop(0)
                bonus.endaction(self)
                del bonus
            
            bubber = self.bubber
            wannafire = bubber.key_fire
            wannajump = bubber.key_jump
            wannago = 0
            if bubber.key_left and bubber.key_left > bubber.key_right:
                wannago = -self.dcap['left2right']
            elif bubber.key_right:
                wannago = self.dcap['left2right']

            if self.dcap['autofire']:
                wannafire = 1
            if self.dcap['pinball']:
                wannajump = 1
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
                self.mytime = (self.mytime+self.dcap['lookforward']) % 12
                hfp += abs(vx)
            else:
                hfp += self.dcap['hspeed']
            while hfp > 0:
                hfp -= 1
                dir = 0
                if wannago == -1:
                    x0 = (self.x+1)//CELL
                    y0 = (self.y+4) // CELL + 1
                    y0bis = (self.y+CELL-1) // CELL + 1
                    if bget(x0,y0) == ' ' == bget(x0,y0bis):
                        dir = -1
                elif wannago == 1:
                    x0 = (self.x-3)//CELL + 2
                    y0 = self.y // CELL + 1
                    y0bis = (self.y+CELL-1) // CELL + 1
                    if bget(x0,y0) == ' ' == bget(x0,y0bis):
                        dir = +1
                self.step(2*dir, 0)
                if dir:
                    self.mytime = (self.mytime+self.dcap['lookforward']) % 12
                else:
                    self.dcap['vslippy'] *= -0.6666
            onbubble = 0
            if not self.dcap['infinite_shield']:
                touching = images.touching(self.x+1, self.y+1, 30, 30)
                touching.reverse()
                for s in touching:
                    if s.touched(self):
                        onbubble = 1
            elif bubber.key_left or bubber.key_right or bubber.key_jump or bubber.key_fire:
                self.dcap['infinite_shield'] = 0

            if self.up:
                mode = 9
                self.up -= self.dcap['gravity']
                if self.up < 4.0:
                    self.up = 0.0
                    #self.key_jump = KeyOff
                    mode = 10
                else:
                    ny = self.y + yfp - self.up
                    if ny < -2*CELL:
                        ny += boards.bheightmod
                    self.move(self.x, int(ny))
                    yfp = ny - self.y
            elif onground(self.x, self.y) or (wannajump and onbubble):
                if wannajump:
                    self.play(images.Snd.Jump)
                    yfp = 0.0
                    self.up = 7.5
                    mode = 9
                else:
                    mode = self.mytime // 4
            else:
                mode = 10
                if self.dcap['fly']:
                    ny = self.y+1
                else:
                    ny = (self.y+4) & ~3
                if ny >= boards.bheight:
                    ny -= boards.bheightmod
                self.move(self.x, ny)

            if wannafire and not self.fire:
                self.fire = 1
                #if boards.curboard.wastingplay is None:
                bubbles.DragonBubble(self, self.x + 4*self.dir, self.y, self.dir)
                #else:
                #    from monsters import DragonShot
                #    DragonShot(self)
            if self.fire:
                if self.fire <= 5:
                    mode = 3
                elif self.fire <= 10:
                    mode = 4
                self.fire += 1
                if self.fire >= 64 // self.dcap['firerate']:
                    self.fire = 0

            s = self.dcap['shield']
            if s:
                if self.dcap['infinite_shield'] and s < 20:
                    s += 4
                s -= 1
                if s & 2:
                    mode = 11
                self.dcap['shield'] = s
            if self.dcap['ring']:# and random.random() > 0.1:
                mode = 11
            self.seticon(self.bubber.icons[mode, self.dir])

            self.watermoveable = not wannajump
            yield None
            
            if self.angry:
                if angryticks == 0:
                    s = ActiveSprite(self.bubber.icons[11, self.dir],
                                     self.x, self.y)
                    s.gen.append(s.die([None], speed=10))
                    angryticks = 6
                angryticks -= 1

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

    def become_monster(self, clsname):
        if self in BubPlayer.DragonList:
            BubPlayer.DragonList.remove(self)
            
            import monsters, mnstrmap
            mcls = getattr(monsters, clsname)
            mdef = getattr(mnstrmap, clsname)
            m = mcls(mdef, self.x, self.y, self.dir, in_list=self.bubber.dragons)
            m.default_mode = m.playing_monster
            m.bubber = self.bubber
            m.gen = [m.becoming_monster(self.dcap)]
            self.gen = [self.killing()]

    def become_bubblingeyes(self, bubble):
        if self in BubPlayer.DragonList:
            BubPlayer.DragonList.remove(self)

            import bubbles
            bubble.to_front()
            m = bubbles.BubblingEyes(self.bubber, self.dcap, bubble)
            self.bubber.dragons.append(m)
            self.gen = [ActiveSprite.die(self, bubbles.Bubble.exploding_bubbles)]
            return 1
        else:
            return 0


class BubPlayer(gamesrv.Player):
    # global state
    PlayerList = []
    DragonList = []
    MonsterList = []
    LimitScore = 0
    LimitScoreColor = None
    LimitTime = None
    #HighScore = 0
    #HighScoreColor = None

    INIT_BOARD_CAP = {
        'FrameCounter': 0,
        'LatestLetsGo': -999,
        'BubblesBecome': None,
        'MegaBonus': None,
        'BaseFrametime': 1.0,
        'LeaveBonus': None,
        }
    TRANSIENT_DATA = ('_client', 'key_left', 'key_right',
                      'key_jump', 'key_fire')

    def __init__(self, n):
        self.pn = n
        self.icons = None
        self.standardplayericon = images.sprget(GreenAndBlue.players[n][3])
        self.reset()

    def reset(self):
        self.letters = {}
        #self.bonbons = 0
        self.points = 0
        self.nextextralife = ExtraLifeEvery
        self.lives = boards.get_lives()
        #self.badpoints = 0
        self.pcap = {}
        self.dragons = []

    def playerjoin(self):
        n = self.pn
        print 'New player is at position #%d.' % n
        if self.icons is None: self.icons = {
            (0, -1): images.sprget(GreenAndBlue.players[n][0]),  # walk
            (0, +1): images.sprget(GreenAndBlue.players[n][3]),
            (1, -1): images.sprget(GreenAndBlue.players[n][1]),
            (1, +1): images.sprget(GreenAndBlue.players[n][4]),
            (2, -1): images.sprget(GreenAndBlue.players[n][2]),
            (2, +1): images.sprget(GreenAndBlue.players[n][5]),
            (3, -1): images.sprget(GreenAndBlue.players[n][6]),  # lancer de bulle
            (3, +1): images.sprget(GreenAndBlue.players[n][8]),
            (4, -1): images.sprget(GreenAndBlue.players[n][7]),
            (4, +1): images.sprget(GreenAndBlue.players[n][9]),
            (5, -1): images.sprget(GreenAndBlue.players[n][0]),  # mort
            (5, +1): images.sprget(GreenAndBlue.players[n][0]),
            (6, -1): images.sprget(GreenAndBlue.players[n][11]),
            (6, +1): images.sprget(GreenAndBlue.players[n][10]),
            (7, -1): images.sprget(GreenAndBlue.players[n][12]),
            (7, +1): images.sprget(GreenAndBlue.players[n][12]),
            (8, -1): images.sprget(GreenAndBlue.players[n][10]),
            (8, +1): images.sprget(GreenAndBlue.players[n][11]),
            (9, -1): images.sprget(GreenAndBlue.jumping_players[n][2]),  # saut, montant
            (9, +1): images.sprget(GreenAndBlue.jumping_players[n][3]),
            (10,-1): images.sprget(GreenAndBlue.jumping_players[n][0]),  # saut, descend
            (10,+1): images.sprget(GreenAndBlue.jumping_players[n][1]),
            (11,-1): images.sprget('shield-left'),    # shielded
            (11,+1): images.sprget('shield-right'),
            }
        self.reset()
        self.key_left  = KeyOff
        self.key_right = KeyOff
        self.key_jump  = KeyOff
        self.key_fire  = KeyOff
        players = [p for p in BubPlayer.PlayerList
                   if p.isplaying() and p is not self]
        self.enterboard(players)
        scoreboard()
        if BubPlayer.LatestLetsGo < BubPlayer.FrameCounter - 30:
            images.Snd.LetsGo.play()
            BubPlayer.LatestLetsGo = BubPlayer.FrameCounter

    def playerleaves(self):
        print 'Closing position #%d.' % self.pn
        self.zarkoff()
        scoreboard()

    def enterboard(self, players):
        leftplayers = [p for p in players if p.start_left]
        rightplayers = [p for p in players if not p.start_left]
        self.start_left = (len(leftplayers) + random.random() <
                           len(rightplayers) + random.random())

    def savecaps(self):
        dragons = [d for d in self.dragons if isinstance(d, Dragon)]
        if dragons:
            for key in Dragon.SAVE_CAP:
                self.pcap[key] = max([d.dcap[key] for d in dragons])

    def zarkoff(self):
        for d in self.dragons[:]:
            d.kill()
        del self.dragons[:]

    def zarkon(self):
        self.key_left  &= 2
        self.key_right &= 2
        self.key_jump  &= 2
        self.key_fire  &= 2
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
        self.key_left = KeyJustPressed
        self.key_right &= 3
    def kmLeft(self):
        self.key_left &= 5
    def kRight(self):
        self.key_right = KeyJustPressed
        self.key_left &= 3
    def kmRight(self):
        self.key_right &= 5
    def kJump(self):
        self.key_jump = KeyJustPressed
    def kmJump(self):
        self.key_jump &= 5
    def kFire(self):
        self.key_fire = KeyJustPressed
    def kmFire(self):
        self.key_fire &= 5

    def bubberdie(self):
        if self.lives is not None and self.lives > 0:
            self.lives -= 1
            scoreboard()

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
            self.nextextralife += ExtraLifeEvery
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


def upgrade(p):
    p.__class__ = BubPlayer
    p.key_left  = KeyOff
    p.key_right = KeyOff
    p.key_jump  = KeyOff
    p.key_fire  = KeyOff
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

def scoreboard(reset=0):
    if reset:
        for p in BubPlayer.PlayerList:
            if len(p.letters) == 6:
                p.letters.clear()
            for key in p.letters:
                p.letters[key] = 2
    brd = boards.curboard
    if not brd or not gamesrv.sprites_by_n:
        return
    lst = []
    bubblesshown = {}
    plist = [(p.points, p) for p in BubPlayer.PlayerList if p.isplaying()]
    plist.sort()
    x0 = boards.bwidth
    y0 = boards.bheight
    for score, p in plist:
        if p.lives == 0:
            ico = images.sprget(GreenAndBlue.gameover[p.pn][0])
            lst.append((x0+9*CELL-ico.w, y0-ico.h, ico))
        else:
            ico = images.sprget(GreenAndBlue.players[p.pn][0])
            lst.append((x0+7*CELL, y0-2*CELL, ico))
        #if boards.curboard.wastingplay is None:
        for l in range(6):
            name = bubbles.extend_name(l)
            if name in p.letters:
                x, y = x0+l*(CELL-1), y0-3*CELL
                imglist = getattr(LetterBubbles, name)
                ico = images.sprget(imglist[1])
                s = p.letters[name]
                if isinstance(s, ActiveSprite):
                    s.move(x, y)
                    bubblesshown[s] = 1
                elif s == 1:
                    s = ActiveSprite(ico, x, y)
                    s.setimages(s.cyclic([imglist[0], imglist[1],
                                          imglist[2], imglist[1]]))
                    p.letters[name] = s
                    bubblesshown[s] = 1
                else:
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
        y0 -= 7*HALFCELL
    for p in BubPlayer.PlayerList:
        for name, s in p.letters.items():
            if isinstance(s, ActiveSprite) and s not in bubblesshown:
                p.letters[name] = 2
                s.kill()
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
    if not brd.bonuslevel:
        xyiconumber(DigitsMisc.digits_white, 2, 2, brd.num+1, lst, width=2)
    brd.writesprites('scoreboard', lst)


# initialize global board data
BubPlayer.__dict__.update(BubPlayer.INIT_BOARD_CAP)
