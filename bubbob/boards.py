from __future__ import generators
import random, os, sys, math
import gamesrv
import images

CELL = 16    # this constant is inlined at some places, don't change
HALFCELL = CELL//2
FRAME_TIME = 0.025
#DEFAULT_LEVEL_FILE = 'levels/scratch.py'

BOARD_BKGND = 1    # 0 = black, 1 = darker larger wall tiles


class Copyable:
    pass   # see bonuses.py, class Clock


class Board(Copyable):
    letter    = 0
    fire      = 0
    lightning = 0
    water     = 0
    top       = 0
    
    WIND_DELTA = HALFCELL

    def __init__(self, num):
        # the subclasses should define 'walls', 'winds', 'monsters'
        self.walls = walls = [line for line in self.walls.split('\n') if line]
        self.winds = winds = [line for line in self.winds.split('\n') if line]
        self.num = num
        self.width = len(walls[0])
        self.height = len(walls)
        for line in walls:
            assert len(line) == self.width, "some wall lines are longer than others"
        for line in winds:
            assert len(line) == self.width, "some wind lines are longer than others"
        #assert walls[0] ==  walls[-1], "first and last lines must be identical"
        assert len(winds) == self.height, "wall and wind heights differ"
        self.walls_by_pos = {}
        self.sprites = {}
        if self.top:
            testline = self.walls[0]
        else:
            testline = self.walls[-1]
        self.holes = testline.find('  ') >= 0
        self.playingboard = 0
        self.bonuslevel = not self.monsters
        self.cleaning_gen_state = 0

    def set_musics(self):
        if (self.num+1) % 20 < 10:
            gamesrv.set_musics([images.music_intro], [images.music_game],
                               reset=0)
        else:
            gamesrv.set_musics([], [images.music_game2], reset=0)

    def writesprites(self, name, xyicolist):
        sprlist = self.sprites.setdefault(name, [])
        xyicolist = xyicolist[:]
        for s in sprlist[:]:
            if xyicolist:
                s.move(*xyicolist.pop(0))
            else:
                s.kill()
                sprlist.remove(s)
        while xyicolist:
            x, y, ico = xyicolist.pop(0)
            sprlist.append(gamesrv.Sprite(ico, x, y))

    def enter(self, complete=1, inplace=0):
        global curboard
        if inplace:
            print "Re -",
        print "Entering board", self.num+1
        self.set_musics()
        # add board walls
        l = self.sprites.setdefault('walls', [])
        bl = self.sprites.setdefault('borderwalls', [])
        if inplace:
            deltay = 0
        else:
            deltay = bheight
        wnx = wny = 1
        while haspat((self.num, wnx, 0)):
            wnx += 1
        while haspat((self.num, 0, wny)):
            wny += 1
        self.wnx = wnx
        self.wny = wny

        if haspat((self.num, 'l')):
            lefticon = patget((self.num, 'l'))
            if haspat((self.num, 'r')):
                righticon = patget((self.num, 'r'))
            else:
                righticon = lefticon
            xrange = range(2, self.width-2)
        else:
            xrange = range(self.width)
            lefticon = righticon = None

        if BOARD_BKGND == 1:
            gl = self.sprites.setdefault('background', [])
            xmax = (self.width-2)*CELL
            ymax = self.height*CELL
            y = -HALFCELL
            ystep = 0
            firstextra = 1
            while y < ymax:
                x = 2*CELL+HALFCELL
                xstep = 0
                while x < xmax:
                    bitmap, rect = loadpattern((self.num, xstep, ystep),
                                               images.KEYCOL)
                    bitmap, rect = images.makebkgndpattern(bitmap, rect)
                    if firstextra:
                        # special position where a bit of black might show up
                        x -= rect[2]
                        xstep = (xstep-1) % wnx
                        firstextra = 0
                        continue
                    bkgndicon = bitmap.geticon(*rect)
                    w = gamesrv.Sprite(bkgndicon, x, y + deltay)
                    gl.append(w)
                    x += rect[2]
                    xstep = (xstep+1) % wnx
                y += rect[3]
                ystep = (ystep+1) % wny
        else:
            gl = []

        if lefticon is not None:
            for y in range(0, self.height, lefticon.h // CELL):
                bl.append(gamesrv.Sprite(lefticon, 0, y*CELL + deltay))

        for y in range(self.height):
            for x in xrange:
                c = self.walls[y][x]
                if c == '#':
                    wallicon = patget((self.num, x%wnx, y%wny), images.KEYCOL)
                    w = gamesrv.Sprite(wallicon, x*CELL, y*CELL + deltay)
                    l.append(w)
                    self.walls_by_pos[y,x] = w

        if righticon is not None:
            for y in range(0, self.height, lefticon.h // CELL):
                bl.append(gamesrv.Sprite(righticon, (self.width-2)*CELL, y*CELL + deltay))

        while deltay:
            dy = -min(deltay, 8)
            for w in gl:
                w.step(0, dy)
            for w in l:
                w.step(0, dy)
            for w in bl:
                w.step(0, dy)
            deltay += dy
            yield 1

        if inplace:
            for w in images.ActiveSprites:
                w.to_front()

        curboard = self
        if not complete:
            return
        # add players
        from player import BubPlayer, scoreboard
        scoreboard(1, inplace=inplace)
        playing = []
        plist = BubPlayer.PlayerList[:]
        random.shuffle(plist)
        for p in plist:
            if p.isplaying():
                p.enterboard(playing)
                p.zarkon()
                playing.append(p)
        # add monsters
        import monsters
        for mdef in self.monsters:
            yield 2
            cls = getattr(monsters, mdef.__class__.__name__)
            cls(mdef)
            if random.random() < (len(playing)-2)/2.2:
                cls(mdef, dir=-mdef.dir)
        self.playingboard = 1

    def putwall(self, x, y, w=None):
        wallicon = patget((self.num, x%self.wnx, y%self.wny), images.KEYCOL)
        if w is None:
            w = gamesrv.Sprite(wallicon, 0, bheight)
            l = self.sprites['walls']
            w.to_back(l[-1])
            l.append(w)
        self.walls_by_pos[y,x] = w
        if y >= 0:
            line = self.walls[y]
            self.walls[y] = line[:x] + '#' + line[x+1:]

    def killwall(self, x, y, kill=1):
        w = self.walls_by_pos[y,x]
        if kill:
            l = self.sprites['walls']
            l.remove(w)
            w.kill()
        del self.walls_by_pos[y,x]
        line = self.walls[y]
        self.walls[y] = line[:x] + ' ' + line[x+1:]
        return w

    def reorder_walls(self):
        walls_by_pos = self.walls_by_pos
        l = self.sprites['walls']
        items = walls_by_pos.items()
        items.sort()
        assert len(items) == len(l)
        for ((y,x), w1), w2 in zip(items, l):
            w2.move(x*CELL, y*CELL)
            walls_by_pos[y,x] = w2

    def leave(self, inplace=0):
        global curboard
        if not gamesrv.has_loop_music():
            gamesrv.fadeout(1.5)
        from player import BubPlayer
        for p in BubPlayer.PlayerList:
            if p.isplaying():
                p.savecaps()
        if BubPlayer.LeaveBonus:
            for t in BubPlayer.LeaveBonus:
                yield t
            BubPlayer.LeaveBonus = None
        curboard = None
        if inplace:
            i = -1
        else:
            while images.ActiveSprites:
                s = random.choice(images.ActiveSprites)
                s.kill()
                yield 0.9
            i = 0
        sprites = []
        for l in self.sprites.values():
            sprites += l
        self.sprites.clear()
        self.walls_by_pos.clear()
        random.shuffle(sprites)
        for s in sprites:
            s.kill()
            if i:
                i -= 1
            else:
                yield 0.32
                i = 3
        if not inplace:
            for p in BubPlayer.PlayerList:
                if p.isplaying():
                    p.zarkoff()
            yield 4

    def clean_gen_state(self):
        self.cleaning_gen_state = 1
        while len(BoardGen) > 1:
            #yield force_singlegen()
            #if 'flood' in self.sprites:
            #    for s in self.sprites['flood']:
            #        s.kill()
            #    del self.sprites['flood']
            yield normal_frame()
        self.cleaning_gen_state = 0

def bget(x, y):
    if 0 <= x < curboard.width:
        if y < 0 or y >= curboard.height:
            y = 0
        return curboard.walls[y][x]
    else:
        return '#'

def wget(x, y):
    delta = curboard.WIND_DELTA
    x = (x + delta) // 16
    y = (y + delta) // 16
    if 0 <= x < curboard.width:
        if y < 0:
            y = 0
        elif y >= curboard.height:
            y = -1
        return curboard.winds[y][x]
    elif x < 0:
        return '>'
    else:
        return '<'

def onground(x, y):
    if y & 15:
        return 0
    x0 = (x+5) // 16
    x1 = (x+16) // 16
    x2 = (x+27) // 16
    y0 = y // 16 + 2

    if x0 < 0 or x2 >= curboard.width:
        return 0
    y1 = y0 - 1
    if not (0 < y0 < curboard.height):
        if y0 != curboard.height:
            y1 = 0
        y0 = 0
    y0 = curboard.walls[y0]
    y1 = curboard.walls[y1]
    return (' ' == y1[x0] == y1[x1] == y1[x2] and
            not (' ' == y0[x0] == y0[x1] == y0[x2]))
    #return (' ' == bget(x0,y0-1) == bget(x1,y0-1) == bget(x2,y0-1) and
    #        not (' ' == bget(x0,y0) == bget(x1,y0) == bget(x2,y0)))
    #return (bget(x1,y0-1)==' ' and
    #        ((bget(x1,y0)=='#') or
    #         (bget(x0,y0)=='#' and bget(x0,y0-1)==' ') or
    #         (bget(x2,y0)=='#' and bget(x2,y0-1)==' ')))

def underground(x, y):
    if y % CELL:
        return 0
    x0 = (x+5) // CELL
    x1 = (x+CELL) // CELL
    x2 = (x+2*CELL-5) // CELL
    y0 = y // CELL

    if x0 < 0 or x2 >= curboard.width:
        return 0
    y1 = y0 - 1
    if not (0 < y0 < curboard.height):
        if y0 != curboard.height:
            y1 = 0
        y0 = 0
    y0 = curboard.walls[y0]
    y1 = curboard.walls[y1]
    return (' ' == y0[x0] == y0[x1] == y0[x2] and
            not (' ' == y1[x0] == y1[x1] == y1[x2]))

def x2bounds(x):
    if x < 32:
        return 32
    elif x > bwidth - 64:
        return bwidth - 64
    else:
        return x

def vertical_warp(nx, ny):
    if ny >= bheight:
        ny -= bheightmod
    elif ny < -32:
        ny += bheightmod
    else:
        return (nx, ny), 0
    from player import BubPlayer
    if BubPlayer.Moebius:
        nx = bwidth - 2*CELL - nx
        return (nx, ny), 1
    else:
        return (nx, ny), 0


MODULES = ['boards', 'bonuses', 'bubbles', 'images',
           'mnstrmap', 'monsters', 'player',
           'binboards', 'macbinary', 'boarddef',
           'ext1', 'ext2', 'ext3', 'ext4']

def loadmodules(force=0):
    levelfilename = gamesrv.game.levelfile
    modulefiles = {None: levelfilename}
    for m in MODULES:
        if os.path.isfile(m+'.py'):
            modulefiles[m] = m+'.py'
        elif os.path.isfile(os.path.join(m, '__init__.py')):
            modulefiles[m] = os.path.join(m, '__init__.py')
    mtimes = {}
    for m, mfile in modulefiles.items():
        mtimes[m] = os.stat(mfile).st_mtime
    reload = force or (mtimes != getattr(sys, 'ST_MTIMES', None))
    import player
    playerlist = player.BubPlayer.PlayerList
    if reload:
        delete = hasattr(sys, 'ST_MTIMES')
        sys.ST_MTIMES = mtimes
        if delete:
            print "Reloading modules."
            for m, mfile in modulefiles.items():
                if m is not None and m in sys.modules:
                    del sys.modules[m]

    # Clear
    gamesrv.clearsprites()
    import images, player
    del images.ActiveSprites[:]
    images.SpritesByLoc.clear()
    
    for p in playerlist:
        player.upgrade(p)
    for n in range(len(playerlist), player.MAX):
        playerlist.append(player.BubPlayer(n))
    player.BubPlayer.PlayerList = playerlist
    if reload:
        import boards
        from images import haspat, loadpattern
        boards.haspat = haspat
        boards.loadpattern = loadpattern
        del boards.BoardList[:]
        if levelfilename.lower().endswith('.py'):
            levels = {}
            print 'Source level file:', levelfilename
            execfile(levelfilename, levels)
            if 'Levels' in levels:
                levels = levels['Levels']
                if isinstance(levels, list):
                    levels = dict(zip(range(len(levels)), levels))
        else:
            import binboards
            levels = binboards.load(levelfilename)
        boards.register(levels)
    return reload

def patget(n, keycol=None):
    bitmap, rect = loadpattern(n, keycol)
    return bitmap.geticon(*rect)

def get_lives():
    return gamesrv.game.limitlives

BoardList = []
curboard = None

def next_board(num=0, complete=1):
    yield force_singlegen()
    set_frametime(1.0)
    brd = curboard
    inplace = 0
    if brd:
        inplace = brd.bonuslevel
        num = brd.num
        if not brd.bonuslevel:
            num += gamesrv.game.stepboard
            if num >= len(BoardList):
                num = len(BoardList)-1
        for t in brd.leave(inplace=inplace):
            yield t

    # reset global board state
    from player import BubPlayer
    BubPlayer.__dict__.update(BubPlayer.INIT_BOARD_CAP)
    if not inplace:
        del BubPlayer.MonsterList[:]

    # wait for at least one player
    while not [p for p in BubPlayer.PlayerList if p.isplaying()]:
        yield 10

    # reload modules if changed
    if not inplace and loadmodules():
        import boards
        boards.BoardGen = [boards.next_board(num)]
        return

    if num < 0:
        num = 0
    elif num >= len(BoardList):
        num = len(BoardList)-1
    brd = BoardList[num](num)
    for t in brd.enter(complete, inplace=inplace):
        yield t

    if brd.bonuslevel:
        gen = bonus_play
    else:
        gen = normal_play
    BoardGen[0] = gen()

def set_frametime(ft):
    from player import BubPlayer
    BubPlayer.BaseFrametime = ft
    images.loadsounds(1.0 / ft)

def extra_boardgen(gen):
    if curboard.playingboard:
        BoardGen.append(gen)

def replace_boardgen(gen, force=0):
    if curboard.playingboard or force:
        curboard.playingboard = 0
        BoardGen[0] = gen

def force_singlegen():
    del BoardGen[1:]
    return 0

def has_singlegen():
    return len(BoardGen) <= 1

def display_hat(p, d):
    if p.team == -1 or getattr(d,'isdying',0) or hasattr(d,'no_hat'):
        return
    try:
        bottom_up = d.bottom_up()
    except AttributeError:
        bottom_up = 0
    try:
        image = ('hat', p.team, d.dir, d.hatangle)
    except AttributeError:
        image = ('hat', p.team)
    if bottom_up:
        ico = images.sprget_vflip(image)
        y = d.y
    else:
        ico = images.sprget(image)
        y = d.y - 16
    if (getattr(d,'hatsprite',None) is None or
        not d.hatsprite.alive):
        d.hatsprite = images.ActiveSprite(ico, d.x, y)
    else:
        d.hatsprite.to_front()
        d.hatsprite.move(d.x, y, ico)
    d.hatsprite.gen = [d.hatsprite.die([None])]

def normal_frame():
    from player import BubPlayer
    BubPlayer.FrameCounter += 1

    # main generator dispatch loop
    images.action(images.ActiveSprites[:])
    
    frametime = 10
    for p in BubPlayer.PlayerList:
        if p.isplaying():
            frametime = BubPlayer.BaseFrametime
            p.zarkon()
            for d in p.dragons:
                d.to_front()
                display_hat(p, d)
                d.prefix(p.pn)
    if not (BubPlayer.FrameCounter & 31):
        gamesrv.compactsprites()
        reset = getattr(BubPlayer, 'MultiplyerReset', 0)
        if reset and BubPlayer.FrameCounter >= reset:
            BubPlayer.MultiplyerReset = 0
            set_frametime(1.0)
    return frametime

def normal_play():
    from player import BubPlayer
    import bonuses
    import bubbles
    framecounter = 0
    while BubPlayer.MonsterList:
        if random.random() < 0.04:
            bonuses.cheatnew()
            if random.random() < 0.15:
                bonuses.newbonus()
            else:
                bubbles.newbubble()
        yield normal_frame()
        if not BubPlayer.DragonList:
            continue
        framecounter += 1
        BASE = 500
        if not (framecounter % BASE):
            if framecounter == 4*BASE:
                from monsters import Monster
                from mnstrmap import BigImages
                ico = images.sprget(BigImages.hurryup[1])
                s = images.ActiveSprite(ico, (bwidth-ico.w)//2, (bheight-ico.h)//2)
                s.setimages(s.die(BigImages.hurryup * 12, 2))
                images.Snd.Hurry.play()
                mlist = [s for s in images.ActiveSprites
                         if (isinstance(s, Monster) and s.regular() and
                             not s.angry)]
                if mlist:
                    s = random.choice(mlist)
                    s.angry = [s.genangry()]
                    s.resetimages()
            if framecounter >= 6*BASE:
                mlist = [s for s in images.ActiveSprites
                         if isinstance(s, Monster) and s.regular() and s.angry]
                if mlist:
                    images.Snd.Hell.play()
                    gamesrv.set_musics([], [])
                    s = random.choice(mlist)
                    s.become_ghost()
                    framecounter = -200
                else:
                    framecounter = 2*BASE
            if framecounter == 0:
                curboard.set_musics()
    replace_boardgen(last_monster_killed())

def last_monster_killed(end_delay=390, music=None):
    from player import BubPlayer
    for t in exit_board(music=music):
        yield t
    if curboard.bonuslevel:
        curboard.playingboard = 1
        play_again = bonus_play()
        for t in play_again:
            yield t
            end_delay -= 1
            if end_delay <= 0:
                replace_boardgen(next_board(), 1)
                break
    else:
        for i in range(end_delay):
            yield normal_frame()
        replace_boardgen(next_board(), 1)

##def bonus_play():
##    from player import BubPlayer
##    import bubbles
##    while BubPlayer.LimitScoreColor is None:
##        yield normal_frame()
##        players = [(p.points, p.pn) for p in BubPlayer.PlayerList
##                   if p.isplaying()]
##        if players:
##            players.sort()
##            points, BubPlayer.LimitScoreColor = players[-1]
##            BubPlayer.LimitScore = ((points + limit) // 100000) * 100000
##    for p in BubPlayer.PlayerList:
##        if p.isplaying():
##            p.givepoints(0)  # check LimitScore and update scoreboard()
##    while not (BubPlayer.BubblesBecome or BubPlayer.MegaBonus):
##        if random.random() < 0.06:
##            bubbles.newbonusbubble()
##        yield normal_frame()
##    # special board end
##    import monsters
##    monsters.argh_em_all()
##    replace_boardgen(last_monster_killed())

class TimeCounter(Copyable):
    def __init__(self, limittime, blink=0):
        from player import BubPlayer
        self.saved_time = BubPlayer.LimitTime
        self.time = limittime / FRAME_TIME
        self.prev = None
        self.blink = blink
    def update(self, t):
        from player import BubPlayer, scoreboard
        self.time -= t
        if self.time < 0.0:
            self.time = 0.0
        BubPlayer.LimitTime = self.time * FRAME_TIME
        next = int(BubPlayer.LimitTime)
        if self.blink and BubPlayer.LimitTime - next >= 0.5:
            BubPlayer.LimitTime = next = None
        if self.prev != next:
            scoreboard()
            self.prev = next
    def restore(self):
        from player import BubPlayer
        BubPlayer.LimitTime = self.saved_time

def bonus_play():
    from player import BubPlayer
    import bubbles
    BubPlayer.MegaBonus = None
    BubPlayer.BubblesBecome = None
    Time0 = 5.0 / FRAME_TIME  # when to slow down time
    tc = TimeCounter(BubPlayer.LimitTime or 180.9)   # 3:00
    prev = None
    while not (BubPlayer.BubblesBecome or BubPlayer.MegaBonus):
        if random.random() < 0.099:
            bubbles.newbonusbubble()
        t = normal_frame()
        tc.update(t)
        if tc.time < Time0:
            if tc.time <= 0.5:
                tc.time = 0.5
                BubPlayer.LimitTime = 0.0
            t *= math.sqrt(Time0 / tc.time)
        yield t
        if tc.time == 0.5:
            gamesrv.game.End = 'gameover'
            replace_boardgen(game_over(), 1)
            return
    # special board end
    import monsters
    monsters.argh_em_all()
    replace_boardgen(last_monster_killed())

def game_over():
    yield force_singlegen()
    from player import BubPlayer, scoreboard
    images.Snd.Extralife.play()
    gamesrv.set_musics([], [images.music_potion])
    scoreboard()
    #maximum = 0
    results = {}
    for p in BubPlayer.PlayerList:
        if p.points:
            results[p] = p.points
            #if p.points > maximum:
            #    maximum = p.points
    maximum = BubPlayer.LimitScore or None #maximum
    for t in result_ranking(results, maximum, None):
        yield t

def game_reset():
    import time
    from player import BubPlayer
    for i in range(int(2.0/FRAME_TIME)):
        yield 0
        if BubPlayer.LimitTime and BubPlayer.LimitTime >= 1.0:
            # someone else ticking the clock, try again later
            return
    # anyone playing ?
    if not gamesrv.game.End:
        return  # yes -> cancel game_reset()
    # let's tick the clock !
    tc = TimeCounter(60.9, blink=1)   # 1:00
    t1 = time.time()
    while tc.time:
        yield 0
        # anyone playing now ?
        if not gamesrv.game.End:
            tc.restore()
            return  # yes -> cancel game_reset()
        t = time.time()  # use real time
        deltat = (t-t1)/FRAME_TIME
        if deltat < 1.0:
            deltat = 1.0
        elif deltat > 100.0:
            deltat = 100.0
        tc.update(deltat)
        t1 = t
    gamesrv.game.reset()

##def wasting_play():
##    from player import BubPlayer, scoreboard
##    import bubbles
##    curboard.wastingplay = {}
##    for p in BubPlayer.PlayerList:
##        if p.isplaying():
##            p.letters = {}
##            p.bonbons = p.points // 50000
##    scoreboard()
    
##    while len(BubPlayer.DragonList) > 1:
##        if random.random() < 0.03:
##            bubbles.newbubble(1)
##        yield normal_frame()
##    for d in BubPlayer.DragonList:
##        curboard.wastingplay[d.bubber] = len(curboard.wastingplay)
##    for i in range(50):
##        yield normal_frame()

##    total = len(curboard.wastingplay)
##    results = [(total-n, p) for p, n in curboard.wastingplay.items()]
##    results.sort()
##    results = [(p, str(n)) for n, p in results]
##    for t in display_ranking(results):
##        yield t
##    # never ending

def skiplevels(blink, skip):
    # (not used any more)
    saved = BoardGen[:]
    while skip:
        skip -= 1
        BoardGen[:] = saved
        for i in range(10):  # frozen pause
            yield 3
            if blink:
                blink.step(-bwidth, 0)
                yield 3.33
                blink.step(bwidth, 0)
        blink = None
        for t in next_board(complete=(skip==0)):
            yield t

def exit_board(delay=8, music=None):
    from bubbles import Bubble
    from bonuses import RandomBonus
    from player import BubPlayer
    from monsters import Monster
    curboard.playingboard = 0
    actives = images.ActiveSprites[:]
    for s in actives:
        if ((isinstance(s, Monster) and s.still_playing())
            or isinstance(s, RandomBonus)):
            s.kill()
    music = music or []
    if BubPlayer.MegaBonus:
        music[:1] = [images.music_modern]
    if music:
        gamesrv.set_musics(music, [])
    for i in range(delay):
        yield normal_frame()
    bubble_outcome = BubPlayer.BubblesBecome or Bubble.pop
    for s in actives:
        if isinstance(s, Bubble):
            bubble_outcome(s)
            yield normal_frame()
    if BubPlayer.MegaBonus:
        BubPlayer.MegaBonus()

def potion_fill(blist):
    from player import BubPlayer
    from bonuses import Bonus
    #timeleft = 1680.0
    for t in exit_board(0, music=[images.music_potion]):
        #timeleft -= t
        yield t
    notes = all_notes = []
    y = 1
    while y < 11 or (y < height-2 and len(all_notes) < 10):
        for x in range(2, width-3, 2):
            if ' ' == bget(x,y) == bget(x+1,y) == bget(x,y+1) == bget(x+1,y+1):
                b = Bonus(x*CELL, y*CELL, falling=0, *blist[((x+y)//2)%len(blist)])
                b.timeout = 444
                all_notes.append(b)
        for i in range(2):
            t = normal_frame()
            #timeleft -= t
            yield t
        y += 2
    while notes: #and timeleft > 0.0:
        notes = [b for b in notes if b.alive]
        t = normal_frame()
        #timeleft -= t
        yield t
    for i in range(10):
        t = normal_frame()
        #timeleft -= t
        yield t
    results = {}
    for b in all_notes:
        for d in b.taken_by:
            bubber = d.bubber
            results[bubber] = results.get(bubber, 0) + 1
    for t in result_ranking(results, len(all_notes)):
        yield t
    #fadeouttime = 3.33
    #fullsoundframes = bonusframes - 10 - int(fadeouttime / FRAME_TIME)
    #for i in range(fullsoundframes):
    #    yield normal_frame()
    #gamesrv.fadeout(fadeouttime)
    #for i in range(fullsoundframes, 490):
    #    yield normal_frame()

def result_ranking(results, maximum=None, timeleft=200):
    if maximum is None:
        maximum = 0
        for n in results.values():
            maximum += n
    maximum = maximum or 1
    ranking = []
    teamrank = [0, 0]
    teamplayers = [[], []]
    for p, n in results.items():
        if p.team != -1:
            teamrank[p.team] += n
            teamplayers[p.team].append((n,p))
        else:
            ranking.append((n, random.random(), p))
    teamplayers[0].sort()
    teamplayers[0].reverse()
    teamplayers[1].sort()
    teamplayers[1].reverse()
    if teamplayers[0] != []:
        ranking.append((teamrank[0], random.random(), teamplayers[0]))
    if teamplayers[1] != []:
        ranking.append((teamrank[1], random.random(), teamplayers[1]))
    ranking.sort()
    ranking.reverse()
    results = []
    for n, dummy, p in ranking:
        results.append((p, str(int(n*100.00001/maximum)) + '%'))
    if curboard.bonuslevel and timeleft is not None:
        play_again = bonus_play()
    else:
        play_again = None
    for t in display_ranking(results, timeleft, play_again):
        yield t
    if gamesrv.game.End != 'gameover':
        replace_boardgen(next_board(), 1)

def display_ranking(ranking, timeleft, bgen=None):
    from mnstrmap import Flood
    from bonuses import Points
    from mnstrmap import DigitsMisc
    waves = []
    if ranking:
        cwidth = 10
        cheight = 3*len(ranking)
        x0 = ((width - cwidth) // 2) * CELL + HALFCELL
        y0 = ((height - cheight) // 2) * CELL + HALFCELL
        extras = curboard.sprites.setdefault('ranking', [])
        wallicon = patget((curboard.num, 0, 0), images.KEYCOL)
        fillicon = images.sprget(Flood.fill)
        waveicons = [images.sprget(n) for n in Flood.waves]
        for y in range(y0-CELL, y0+cheight*CELL+CELL, CELL):
            w = gamesrv.Sprite(wallicon, x0-CELL, y)
            extras.append(w)
        for x in range(x0, x0+cwidth*CELL, CELL):
            w = gamesrv.Sprite(wallicon, x, y0+cheight*CELL)
            extras.append(w)
            for y in range(y0, y0+cheight*CELL, CELL):
                w = gamesrv.Sprite(fillicon, x, y)
                extras.append(w)
            w = gamesrv.Sprite(waveicons[-1], x, y0-CELL)
            extras.append(w)
            waves.append(w)
        for y in range(y0-CELL, y0+cheight*CELL+CELL, CELL):
            w = gamesrv.Sprite(wallicon, x0+cwidth*CELL, y)
            extras.append(w)

        map = {'%': 'percent'}
        for digit in range(10):
            map[str(digit)] = DigitsMisc.digits_white[digit]
        y = y0 + HALFCELL
        if timeleft is None:
            nbpoints = 0
        else:
            nbpoints = ((len(ranking)+1)//2)*10000
        for i in range(len(ranking)):
            bubber, text = ranking[i]
            text = [map[digit] for digit in text]
            if i == 0:
                icon = 10
            elif i == len(ranking) - 1:
                icon = 9
            else:
                icon = 0
            x = x0 + 22
            if nbpoints > 0:
                if isinstance(bubber,list):
                    for n, bub in bubber:
                        bub.givepoints(nbpoints//len(bubber))
                    if bubber != []:
                        Points(x, y, bubber[0][1].pn, nbpoints)
                else:
                    bubber.givepoints(nbpoints)
                    Points(x, y, bubber.pn, nbpoints)
                nbpoints -= 10000
            if isinstance(bubber,list):
                w = gamesrv.Sprite(images.sprget(('hat',bubber[0][1].team)), x, y)
            else:
                w = gamesrv.Sprite(bubber.icons[icon, +1], x, y)
            extras.append(w)
            w0 = 0
            for digit in text:
                w0 += images.sprget(digit).w+1
            x = x0 + (22 + 2*CELL + cwidth*CELL - w0) // 2
            for digit in text:
                icon = images.sprget(digit)
                w = gamesrv.Sprite(icon, x, y + CELL - icon.h//2)
                extras.append(w)
                x += icon.w+1
            y += 3*CELL
    #if timeleft is not None and timeleft < 100.0:
    #    timeleft = 100.0
    while timeleft is None or timeleft > 0.0:
        if waves:
            ico = waveicons.pop(0)
            waveicons.append(ico)
            for w in waves:
                w.seticon(ico)
        if timeleft is None:
            yield 2
        else:
            for i in range(2):
                if bgen is None:
                    t = normal_frame()
                else:
                    try:
                        t = bgen.next()
                    except StopIteration:
                        timeleft = 0.0
                        break
                timeleft -= t
                yield t
    gamesrv.set_musics([], [])

def extra_water_flood():
    from mnstrmap import Flood
    from monsters import Monster
    waves_icons = [images.sprget(n) for n in Flood.waves]
    fill_icon = images.sprget(Flood.fill)
    bspr = []
    if 'flood' in curboard.sprites:
        return    # only one flooding at a time
    curboard.sprites['flood'] = bspr
    waves_sprites = [gamesrv.Sprite(waves_icons[0], x, bheight-CELL)
                     for x in range(0, bwidth, CELL)]
    bspr += waves_sprites
    fill_by_line = []
    poplist = [None]
    while waves_sprites[0].y > 0:
        yield 0
        waves_icons.insert(0, waves_icons.pop())
        for s in waves_sprites:
            s.seticon(waves_icons[0])
        yield 0
        sprites = [gamesrv.Sprite(fill_icon, s.x, s.y) for s in waves_sprites]
        bspr += sprites
        fill_by_line.append(sprites)
        for s in waves_sprites:
            s.step(0, -16)
        for s in images.touching(0, waves_sprites[0].y, bwidth, bheight):
            if isinstance(s, Monster):
                s.argh(poplist)
    while 1:
        for i in range(2):
            yield 0
            waves_icons.insert(0, waves_icons.pop())
            for s in waves_sprites:
                s.seticon(waves_icons[0])
        if not fill_by_line:
            break
        for s in fill_by_line.pop():
            s.kill()
        for s in waves_sprites:
            s.step(0, 16)
    for s in waves_sprites:
        s.kill()
    del curboard.sprites['flood']

def extra_walls_falling():
    walls_by_pos = curboard.walls_by_pos
    moves = 1
    while moves and not curboard.cleaning_gen_state:
        moves = 0
        for y in range(height-3, -1, -1):
            for x in range(2, width-2):
                if ((y,x) in walls_by_pos and
                    (y+1,x) not in walls_by_pos and
                    (y+2,x) not in walls_by_pos):
                    y0 = y
                    while (y0-1,x) in walls_by_pos:
                        y0 -= 1
                    w = curboard.killwall(x, y0, 0)
                    curboard.putwall(x, y+1, w)
                    moves = 1
        curboard.reorder_walls()
        for y in range(height):
            yield 0

def single_blocks_falling(xylist):
    walls_by_pos = curboard.walls_by_pos
    while xylist:
        newlist = []
        for x, y in xylist:
            if ((y,x) in walls_by_pos and (y+1,x) not in walls_by_pos and
                y < curboard.height-1):
                newlist.append((x, y+1))
        for x, y in newlist:
            w = curboard.killwall(x, y-1, 0)
            curboard.putwall(x, y, w)
        xylist = newlist
        curboard.reorder_walls()
        for i in range(7):
            yield 0

def extra_display_repulse(cx, cy, dlimit=5000, dfactor=1000):
    offsets = {}
    for s in gamesrv.sprites_by_n.values():
        x, y = s.getdisplaypos()
        if x is not None:
            dx = x - cx
            dy = y - cy
            d = dx*dx + dy*dy + 100
            if d <= dlimit:
                dx = (dx*dfactor)//d
                dy = (dy*dfactor)//d
                offsets[s] = dx, dy
                s.setdisplaypos(x+dx, y+dy)
    yield 0
    yield 0
    while offsets:
        prevoffsets = offsets
        offsets = {}
        for s, (dx, dy) in prevoffsets.items():
            if s.alive:
                if dx < 0:
                    dx += max(1, (-dx)//5)
                elif dx:
                    dx -= max(1, dx//5)
                if dy < 0:
                    dy += max(1, (-dy)//5)
                elif dy:
                    dy -= max(1, dy//5)
                if dx or dy:
                    offsets[s] = dx, dy
                s.setdisplaypos(s.x+dx, s.y+dy)
        yield 0

def extra_bkgnd_black(cx, cy):
    gl = curboard.sprites.get('background')
    dist = 0
    while gl:
        dist += 17
        dist2 = dist * dist
        gl2 = []
        for s in gl:
            if (s.x-cx)*(s.x-cx) + (s.y-cy)*(s.y-cy) < dist2:
                s.kill()
            else:
                gl2.append(s)
        gl[:] = gl2
        yield 0

def register(dict):
    global width, height, bwidth, bheight, bheightmod
    items = dict.items()
    items.sort()
    for name, board in items:
        try:
            if not issubclass(board, Board) or board is Board:
                continue
        except TypeError:
            continue
        BoardList.append(board)
    # check sizes
    assert BoardList, "board file does not define any board"
    B = BoardList[0]
    try:
        test = B(-1)
        width = test.width
        height = test.height
        for B in BoardList[1:]:
            test = B(-1)
            assert test.width == width, "some boards have a different width"
            assert test.height == height, "some boards have a different height"
    except Exception, e:
        print 'Caught "%s" in level "%s":' % (e, B.__name__)
        raise e
    bwidth = width*CELL
    bheight = height*CELL
    bheightmod = (height+2)*CELL

##def define_boards(filename):
##    global curboard, boards, width, height, bwidth, bheight, bheightmod
##    curboard = None
##    boards = []
##    def board((wallfile, wallrect), shape):
##        lines = shape.strip().split('\n')
##        bmp = gamesrv.getbitmap(wallfile)
##        wallicon = bmp.geticon(*wallrect)
##        boards.append(Board(lines, wallicon))
##    d = {'board': board}
##    execfile(filename, d)
##    assert boards, "board file does not define any board"
##    width = boards[0].width
##    height = boards[0].height
##    for b in boards[1:]:
##        assert b.width == width, "some boards have a different width"
##        assert b.height == height, "some boards have a different height"
##    bwidth = width*CELL
##    bheight = height*CELL
##    bheightmod = len(boards[0].lines)*CELL


#try:
#    import psyco
#except ImportError:
#    pass
#else:
#    psyco.bind(normal_frame)
