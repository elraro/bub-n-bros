from __future__ import generators
import random, os, sys, math
import gamesrv
import images

CELL = 16
HALFCELL = CELL//2
FRAME_TIME = 0.025
DEFAULT_LEVEL_FILE = 'levels/scratch.py'


class Board:
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
            for y in range(0, self.height, lefticon.h // CELL):
                bl.append(gamesrv.Sprite(lefticon, 0, y*CELL + deltay))
        else:
            xrange = range(self.width)
            righticon = None
        
        for y in range(self.height):
            for x in xrange:
                c = self.walls[y][x]
                if c == '#':
                    wallicon = patget((self.num, x%wnx, y%wny), images.KEYCOL)
                    w = gamesrv.Sprite(wallicon, x*CELL, y*CELL + deltay)
                    l.append(w)
                    self.walls_by_pos[y,x] = w

        if righticon is not None:
            n = len(bl)
            for y in range(0, self.height, lefticon.h // CELL):
                bl.append(gamesrv.Sprite(righticon, (self.width-2)*CELL, y*CELL + deltay))

        while deltay:
            dy = -min(deltay, 6)
            for w in l:
                w.step(0, dy)
            for w in bl:
                w.step(0, dy)
            deltay += dy
            yield 0.77

        if inplace:
            for w in images.ActiveSprites:
                w.to_front()

        curboard = self
        if not complete:
            return
        # add players
        from player import BubPlayer, scoreboard
        scoreboard(1)
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
        l = self.sprites['walls']
        items = self.walls_by_pos.items()
        items.sort()
        assert len(items) == len(l)
        for ((y,x), w1), w2 in zip(items, l):
            w2.move(x*CELL, y*CELL)

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


def bget(x, y):
    if 0 <= x < curboard.width:
        if y < 0 or y >= curboard.height:
            y = 0
        return curboard.walls[y][x]
    else:
        return '#'

def wget(x, y):
    x = (x + curboard.WIND_DELTA) // CELL
    y = (y + curboard.WIND_DELTA) // CELL
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
    if y % CELL:
        return 0
    x0 = (x+5) // CELL
    x1 = (x+CELL) // CELL
    x2 = (x+2*CELL-5) // CELL
    y0 = y // CELL + 2

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

def x2bounds(x):
    if x < 2*CELL:
        return 2*CELL
    elif x > bwidth - 4*CELL:
        return bwidth - 4*CELL
    else:
        return x

def vertical_warp(nx, ny):
    if ny >= bheight:
        ny -= bheightmod
    elif ny < -2*CELL:
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
           'binboards', 'macbinary', 'boarddef']

def loadmodules(delete):
    levelfilename = getattr(sys, 'ST_LVLFILE', DEFAULT_LEVEL_FILE)
    modulefiles = {None: levelfilename}
    for m in MODULES:
        modulefiles[m] = m+'.py'
    mtimes = {}
    for m, mfile in modulefiles.items():
        mtimes[m] = os.stat(mfile).st_mtime
    reload = mtimes != getattr(sys, 'ST_MTIMES', None)
    import player
    playerlist = player.BubPlayer.PlayerList
    if reload:
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
        del boards.BoardList[:]
        if levelfilename.lower().endswith('.py'):
            levels = {}
            print 'Source level file:', levelfilename
            execfile(levelfilename, levels)
        else:
            import binboards
            levels = binboards.load(levelfilename)
        boards.register(levels)
    return reload

patget = images.patget
haspat = images.haspat

def set_levelfile(lvlfile):
    sys.ST_LVLFILE = lvlfile

def set_lives(lives):
    sys.ST_LIVES = lives

def get_lives():
    return getattr(sys, 'ST_LIVES', None)

def set_boardstep(boardstep):
    sys.ST_BOARDSTEP = boardstep

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
            num += getattr(sys, 'ST_BOARDSTEP', 1)
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
    if not inplace and loadmodules(1):
        import boards
        boards.BoardGen = [boards.next_board(num)]
        return

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

def normal_frame():
    from player import BubPlayer
    BubPlayer.FrameCounter += 1
    #BubPlayer.RealtimeRatio **= 0.99
    alldragons = {}
    frametime = 10
    for p in BubPlayer.PlayerList:
        if p.isplaying():
            frametime = BubPlayer.BaseFrametime
            p.zarkon()
            for d in p.dragons:
                d.to_front()
    if not (BubPlayer.FrameCounter & 31):
        gamesrv.compactsprites()
        reset = getattr(BubPlayer, 'MultiplyerReset', 0)
        if reset and BubPlayer.FrameCounter >= reset:
            BubPlayer.MultiplyerReset = 0
            set_frametime(1.0)
    
    for s in images.ActiveSprites[:]:
        s.action()
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
                    s.angry = 1
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

def bonus_play():
    from player import BubPlayer, scoreboard
    import bubbles
    BubPlayer.MegaBonus = None
    BubPlayer.BubblesBecome = None
    Time0 = 5.0 / FRAME_TIME  # when to slow down time
    if BubPlayer.LimitTime is None:
        BubPlayer.LimitTime = 180.9  # 2:30
    time = BubPlayer.LimitTime / FRAME_TIME
    prev = None
    while not (BubPlayer.BubblesBecome or BubPlayer.MegaBonus):
        if random.random() < 0.099:
            bubbles.newbonusbubble()
        t = normal_frame()
        time -= t
        BubPlayer.LimitTime = time * FRAME_TIME
        if time < Time0:
            if time <= 0.5:
                time = 0.5
                BubPlayer.LimitTime = 0.0
            t *= math.sqrt(Time0 / time)
        next = int(BubPlayer.LimitTime)
        if prev != next:
            scoreboard()
            prev = next
        yield t
        if time == 0.5:
            replace_boardgen(game_over(), 1)
            return
    # special board end
    import monsters
    monsters.argh_em_all()
    replace_boardgen(last_monster_killed())

def game_over():
    # when a player reaches the LimitScore
    yield force_singlegen()
    from player import BubPlayer
    images.Snd.Extralife.play()
    gamesrv.set_musics([], [images.music_potion])
    players = [(p.points, p) for p in BubPlayer.PlayerList if p.isplaying()]
    players.sort()
    maximum = BubPlayer.LimitScore or (players and players[-1][0]) or 1
    ranking = []
    for points, p in players:
        percent = int(points*100.00001/maximum)
        ranking.insert(0, (p, str(percent) + '%'))
    for t in display_ranking(ranking, None):
        yield t  # never ending

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
    if BubPlayer.MegaBonus:
        music = [images.music_modern]
    if music is not None:
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
    ranking = []
    for p in BubPlayer.PlayerList:
        n = results.get(p)
        if n:
            ranking.append((n, random.random(), p))
    ranking.sort()
    ranking.reverse()
    results = []
    for n, dummy, p in ranking:
        results.append((p, str(int(n*100.00001/len(all_notes))) + '%'))
    if curboard.bonuslevel:
        play_again = bonus_play()
    else:
        play_again = None
    for t in display_ranking(results, 200, play_again):
        yield t
    replace_boardgen(next_board(), 1)
    #fadeouttime = 3.33
    #fullsoundframes = bonusframes - 10 - int(fadeouttime / FRAME_TIME)
    #for i in range(fullsoundframes):
    #    yield normal_frame()
    #gamesrv.fadeout(fadeouttime)
    #for i in range(fullsoundframes, 490):
    #    yield normal_frame()

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
                bubber.givepoints(nbpoints)
                Points(x, y, bubber.pn, nbpoints)
                nbpoints -= 10000
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
    atom = object()
    bspr = []
    curboard.sprites['flood', atom] = bspr
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
            s.step(0, -CELL)
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
            s.step(0, CELL)
    for s in waves_sprites:
        s.kill()
    del curboard.sprites['flood', atom]

def extra_walls_falling():
    walls_by_pos = curboard.walls_by_pos
    moves = 1
    while moves:
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
            yield 0
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

def register(dict):
    global width, height, bwidth, bheight, bheightmod
    if hasattr(dict, '__dict__'):
        dict = dict.__dict__
    items = dict.items()
    items.sort()
    for name, board in items:
        try:
            if not issubclass(board, Board) or board is Board or board.__name__ == 'RandomLevel':
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
    except:
        print 'In level "%s":' % B.__name__
        raise
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
