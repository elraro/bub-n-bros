from __future__ import generators
import os, random
import images, gamesrv
from images import ActiveSprite
import boards
from boards import CELL, HALFCELL, bget
from player import Dragon, BubPlayer
from mnstrmap import Monky

LocalDir = os.path.basename(os.path.dirname(__file__))

localmap = {
    'trn-h':   ('image1-%d.ppm', (0, 16, 16, 5)),
    'trn-v':   ('image1-%d.ppm', (0, 0, 5, 16)),
    'trn-bg':  ('image2.ppm',    (0, 0, 32, 32)),
    }

music = gamesrv.getmusic(os.path.join(LocalDir, 'music.wav'))
snd_crash = gamesrv.getsample(os.path.join(LocalDir, 'crash.wav'))


class TronHead(ActiveSprite):

    def __init__(self, tron, bubber, dcap, cx, cy, dir):
        self.tron = tron
        self.bubber = bubber
        self.dcap = dcap
        self.cx = cx
        self.cy = cy
        self.dir = dir
        self.ico_h = images.sprget(('trn-h', bubber.pn))
        self.ico_v = images.sprget(('trn-v', bubber.pn))
        ActiveSprite.__init__(self, *self.trail())
        self.gen.append(self.turning())
        self.gen.append(self.trailing())

    def trail(self):
        cx = self.cx * CELL + 2
        cy = self.cy * CELL + 2
        if self.dir == (1, 0):  return self.ico_h, cx-CELL, cy-2
        if self.dir == (-1, 0): return self.ico_h, cx, cy-2
        if self.dir == (0, 1):  return self.ico_v, cx-2, cy-CELL
        if self.dir == (0, -1): return self.ico_v, cx-2, cy
        raise ValueError, self.dir

    def turning(self):
        lastwannago = None
        while True:
            wannago = self.bubber.wannago(self.dcap)
            if wannago != lastwannago:
                dx, dy = self.dir
                if wannago < 0: dx, dy = dy, -dx
                if wannago > 0: dx, dy = -dy, dx
                self.dir = dx, dy
                lastwannago = wannago
            yield None

    def trailing(self):
        unoccupied = self.tron.unoccupied
        trailsprites = self.tron.trailsprites
        while True:
            self.cx += self.dir[0]
            self.cy += self.dir[1]
            if not unoccupied.get((self.cx, self.cy)):
                self.crash()
            unoccupied[self.cx, self.cy] = False
            trailsprites.append(gamesrv.Sprite(*self.trail()))
            yield None
            yield None
            yield None
            yield None

    def crash(self):
        self.play(snd_crash)
        ico = images.sprget(Monky.decay_weapon[1])
        s = ActiveSprite(ico, self.cx * CELL + 2 - CELL,
                              self.cy * CELL + 2 - CELL)
        s.gen.append(s.die(Monky.decay_weapon[2:], 4))
        self.stop()

    def stop(self):
        del self.gen[:]
        try:
            self.tron.trons.remove(self)
        except ValueError:
            pass

    def kill(self):
        self.stop()
        try:
            self.bubber.dragons.remove(self)
        except ValueError:
            pass
        ActiveSprite.kill(self)


class Tron:
    
    def bgen(self, limittime = 60.1): # 1:00
        for t in boards.exit_board(0, repeatmusic=[music]):
            yield t
        for t in curboard.clean_gen_state():
            yield t

        self.ready = 0
        self.trons = []
        self.trailsprites = []
        self.score = {}
        self.playerlist = BubPlayer.PlayerList[:]
        tc = boards.TimeCounter(limittime)
        for t in self.frame(tc):
            t = boards.normal_frame()
            self.build_trons()
            yield t
            tc.update(t)

        self.ready = 0
        tc.restore()
        for t in boards.result_ranking(self.score):
            self.remove_trons()
            yield t
        self.remove_trons()

    def build_trons(self):
        if self.ready == 0:
            self.remove_trons()
            return
        for p in self.playerlist:
            dragons = [d for d in p.dragons if not isinstance(d, TronHead)]
            if self.ready < 10 and dragons and len(p.dragons) == len(dragons):
                self.score.setdefault(p, 0)
                dragon = random.choice(dragons)
                x, y, dir = self.select_start_point()
                head = TronHead(self, p, dragon.dcap, x, y, dir)
                self.unoccupied[x, y] = False
                self.trons.append(head)
                p.dragons.append(head)
                #p.emotic(head, 4)
            for d in dragons:
                d.kill()

    def remove_trons(self):
        for p in BubPlayer.PlayerList:
            for d in p.dragons[:]:
                d.kill()
        for s in self.trailsprites:
            s.kill()
        del self.trailsprites[:]

    def select_start_point(self):
        distmin = 10
        while True:
            x, y, dir = random.choice(self.start_points)
            for head in self.trons:
                if abs(x-head.cx) + abs(y-head.cy) < distmin:
                    break
            else:
                return x, y, dir
            distmin *= 0.9

    def frame(self, tc):
        l = curboard.sprites['walls']
        gl = curboard.sprites.setdefault('background', [])
        bkgndicon = images.sprget('trn-bg')
        for x in range(2, curboard.width-2):
            for y in range(1, curboard.height-1):
                if (y, x) in curboard.walls_by_pos:
                    curboard.killwall(x, y)
            for y in [0, curboard.height-1]:
                if (y, x) not in curboard.walls_by_pos:
                    curboard.putwall(x, y)
            curboard.reorder_walls()
            if x % 2 == 0:
                for y in range(0, curboard.height, 2):
                    w = gamesrv.Sprite(bkgndicon, x*CELL + HALFCELL,
                                                  y*CELL + HALFCELL)
                    w.to_back(l[0])
                    gl.append(w)
            yield None

        self.unoccupied = {}
        self.start_points = []
        for x in range(4, curboard.width-5):
            self.start_points.append((x, 2, (0, 1)))
            self.start_points.append((x, curboard.height-2, (0, -1)))

        while tc.time != 0.0:
            for x in range(3, curboard.width-2):
                for y in range(2, curboard.height-1):
                    self.unoccupied[x, y] = True
            random.shuffle(self.playerlist)

            min_players = 1
            while self.ready < 20 or len(self.trons) >= min_players:
                if len(self.trons) >= 2:
                    min_players = 2
                self.ready += 1
                yield None

            if len(self.trons) == 1:
                self.score[self.trons[0].bubber] += 1
                self.trons[0].stop()
                self.ready = 99

            for i in range(20):
                yield None
            self.ready = 0
            for i in range(5):
                yield None


def run():
    global curboard
    from boards import curboard
    boards.replace_boardgen(Tron().bgen())

def setup():
    for key, (filename, rect) in localmap.items():
        filename = os.path.join(LocalDir, filename)
        if filename.find('%d') >= 0:
            for p in BubPlayer.PlayerList:
                images.sprmap[key, p.pn] = (filename % p.pn, rect)
        else:
            images.sprmap[key] = (filename, rect)
setup()
