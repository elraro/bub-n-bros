from __future__ import generators
import os, math, random
import images
from images import ActiveSprite
from boards import CELL, HALFCELL, FRAME_TIME
from mnstrmap import GreenAndBlue
from bubbles import BubblingEyes


localmap = {
    'ark-paddle':  ('image1-%d.ppm', (0, 0, 96, 32)),
    }


def aget(x, y):
    if 0 <= x < curboard.width and y >= 0:
        if y >= curboard.height:
            return ' '
        return curboard.walls[y][x]
    else:
        return '#'

def sign(x):
    if x >= 0.0:
        return 1
    else:
        return -1


class PaddleEyes(BubblingEyes):

    def __init__(self, bubber, saved_caps, paddle):
        BubblingEyes.__init__(self, bubber, saved_caps, paddle)
        self.deltax = (paddle.ico.w - self.ico.w) // 2
        self.deltay = (paddle.ico.h - self.ico.h) // 2
        self.step(self.deltax, self.deltay)

    def playing_bubble(self, paddle, accel=0.4, vmax=4.0):
        import boards
        dx = self.deltax
        dy = self.deltay
        bubber = paddle.bubber
        vx = 0.0
        fx = paddle.x
        while paddle.alive:
            wannago = bubber.wannago(self.saved_caps)
            if paddle.timeleft is None:
                keydy = 0
            else:
                keydy = -1
            key = ('eyes', wannago, keydy)
            if fx < 2*CELL:
                if vx < 0.0:
                    vx = -vx * 0.45
                wannago = 1
            elif fx + paddle.ico.w > boards.bwidth - 2*CELL:
                if vx > 0.0:
                    vx = -vx * 0.45
                wannago = -1
            if not wannago:
                if -accel <= vx <= accel:
                    vx = 0
                elif vx < 0.0:
                    wannago = 0.7
                else:
                    wannago = -0.7
            vx += accel * wannago
            if vx < -vmax:
                vx = -vmax
            elif vx > vmax:
                vx = vmax
            fx += vx
            paddle.move(int(fx), paddle.y)
            self.move(paddle.x+dx, paddle.y+dy, images.sprget(key))
            yield None
        self.kill()

    def bottom_up(self):
        return 0


class Paddle(ActiveSprite):

    def __init__(self, arkanoid, bubber, px, py):
        ico = images.sprget(('ark-paddle', bubber.pn))
        ActiveSprite.__init__(self, ico, px - (ico.w-2*CELL)//2,
                                         py - (ico.h-2*CELL)//2)
        self.arkanoid = arkanoid
        self.bubber = bubber
        self.timeleft = None
        self.gen.append(self.bounce_down())
        self.gen.append(self.order())
        self.arkanoid.paddles.append(self)

    def bounce_down(self):
        import boards
        target_y = boards.bheight - self.ico.h
        fy = self.y
        vy = 0.0
        while fy < target_y or abs(vy) > 0.3:
            if fy < target_y:
                vy += 0.3
            elif vy > 0.0:
                vy = -vy / 3.0
            fy += vy
            self.move(self.x, int(fy))
            yield None
        while self.y > target_y:
            self.step(0, -2)
            yield None
        self.move(self.x, target_y)
        self.gen.append(self.wait_and_shoot())

    def wait_and_shoot(self):
        timeout = 40
        while timeout > 0:
            timeout -= self.arkanoid.ready
            yield None
        self.gen.append(self.catch(Ball(self)))

    def catch(self, ball):
        import boards
        while ball.alive:
            if ball.y > boards.bheight//2+1 and ball.vy > 0.0:
                deltay = self.y - Ball.Y_MARGIN - ball.y
                self.timeleft = deltay / ball.vy
                #if -1.25 <= self.timeleft <= 0.5:
                if -12 <= deltay <= 1:
                    ball.bouncepad(self.arkanoid.paddles)
            else:
                self.timeleft = None
            yield None
        if ball.missed:
            self.kill()

    def kill(self):
        from bubbles import Bubble
        ico = images.sprget(Bubble.exploding_bubbles[0])
        for i in range(11):
            s = ActiveSprite(ico,
                             self.x + random.randrange(self.ico.w) - CELL,
                             self.y + random.randrange(self.ico.h) - CELL)
            s.gen.append(s.die(Bubble.exploding_bubbles))
        try:
            self.arkanoid.paddles.remove(self)
        except ValueError:
            pass
        ActiveSprite.kill(self)

    def order(self):
        while 1:
            if self.timeleft is not None:
                self.arkanoid.order.append((self.timeleft, self))
            yield None

    def score(self):
        self.arkanoid.bricks[self.bubber] += 1
        self.bubber.givepoints(50)


class Ball(ActiveSprite):

    Y_MARGIN = 20
    SPEED = 5.8
    
    def __init__(self, paddle):
        self.paddle = paddle
        imglist1 = GreenAndBlue.new_bubbles[paddle.bubber.pn]
        ActiveSprite.__init__(self, images.sprget(imglist1[0]),
                              paddle.x + CELL,
                              paddle.y - Ball.Y_MARGIN)
        self.missed = 0
        self.setimages(self.imgseq(imglist1[1:], 6))
        self.bounceangle(-0.375)
        self.gen.append(self.flying())

    def bouncepad(self, paddles):
        for paddle in paddles:
            dx = (self.x + self.ico.w//2) - (paddle.x + paddle.ico.w//2)
            dxmax = paddle.ico.w//2
            angle = float(dx) / dxmax
            if 0.0 <= angle <= 1.0:
                self.bounceangle(angle * 1.111 + 0.07)
                return 1
            if -1.0 <= angle <= 0.0:
                self.bounceangle(angle * 1.111 - 0.07)
                return -1
        return 0

    def bounceangle(self, angle):
        self.vx = math.sin(angle) * self.SPEED
        self.vy = - math.cos(angle) * self.SPEED

    def flying(self):
        import boards
        fx = self.x
        fy = self.y
        while self.y < boards.bheight:
            fx += self.vx
            fy += self.vy
            self.move(int(fx), int(fy))
            yield None
            cx = (self.x+HALFCELL) // CELL
            cy = (self.y+HALFCELL) // CELL
            dx = sign(self.vx)
            dy = sign(self.vy)
            if aget(cx+dx, cy) == '#':
                self.ahit(cx+dx, cy, 0, dy)
                self.vx = -self.vx
            if aget(cx, cy+dy) == '#':
                self.ahit(cx, cy+dy, dx, 0)
                self.vy = -self.vy
        self.missed = 1
        self.kill()

    def ahit(self, cx, cy, dx, dy):
        for i in (-1, 0, 1):
            x = cx + i*dx
            y = cy + i*dy
            if (2 <= x < curboard.width - 2 and 0 <= y < curboard.height and
                aget(x, y) == '#'):
                curboard.killwall(x, y)
                self.paddle.score()

    def pop(self):
        from bubbles import Bubble
        self.play(images.Snd.Pop)
        self.gen = [self.die(Bubble.exploding_bubbles)]


class Arkanoid:
    
    def bgen(self, limittime = 30.1): # 0:30
        import boards
        from player import BubPlayer

        for t in boards.exit_board(0):
            yield t
        yield boards.force_singlegen()

        tc = boards.TimeCounter(limittime)
        self.ready = 0
        self.bricks = {}
        self.nbbricks = 0
        self.order = []
        self.paddles = []
        finish = 0
        for t in self.frame():
            self.order_paddles()
            t = boards.normal_frame()
            self.build_paddles()
            yield t
            if len(self.paddles) == 0:
                finish += 1
                if finish == 20:
                    break
            else:
                finish = 0
            if self.ready:
                tc.update(t)
                if tc.time == 0.0:
                    break

        self.ready = 0
        for s in images.ActiveSprites[:]:
            if isinstance(s, Ball):
                s.pop()
        for t in boards.result_ranking(self.bricks, self.nbbricks):
            self.build_paddles()
            yield t
        self.remove_paddles()
        tc.restore()

    def frame(self):
        for y in range(curboard.height-1, curboard.height//2, -1):
            yield None
            yield None
            for x in range(2, curboard.width-2):
                if aget(x, y) == '#':
                    curboard.killwall(x, y)
        brickline = curboard.width-4
        expected = brickline * (curboard.height//4)
        y = curboard.height//2
        nbbricks = 0
        while y>=0 and nbbricks + (y+1)*brickline >= expected:
            yield None
            for x in range(2, curboard.width-2):
                if aget(x, y) == '#':
                    nbbricks += 1
            y -= 1
        while y >= -1:
            yield None
            yield None
            for x in range(2, curboard.width-2):
                if y < 0 or aget(x, y) == ' ':
                    curboard.putwall(x, y)
            curboard.reorder_walls()
            y -= 1
        
        self.ready = 1
        self.nbbricks = len(curboard.walls_by_pos) - brickline
        while len(curboard.walls_by_pos) > brickline:
            yield None

    def build_paddles(self):
        from player import BubPlayer
        for p in BubPlayer.PlayerList:
            dragons = [d for d in p.dragons if not isinstance(d, PaddleEyes)]
            if (dragons and len(p.dragons) == len(dragons) and
                p not in self.bricks):
                dragon = random.choice(dragons)
                self.bricks[p] = 0
                paddle = Paddle(self, p, dragon.x, dragon.y)
                eyes = PaddleEyes(p, dragon.dcap, paddle)
                p.dragons.append(eyes)
                p.emotic(dragon, 4)
            for d in dragons:
                d.kill()

    def order_paddles(self):
        self.order.sort()
        self.order.reverse()
        for timeleft, paddle in self.order:
            try:
                self.paddles.remove(paddle)
            except ValueError:
                pass
            else:
                self.paddles.insert(0, paddle)
                paddle.to_front()
        del self.order[:]

    def remove_paddles(self):
        killclasses = (Paddle, PaddleEyes, Ball)
        for s in images.ActiveSprites[:]:
            if isinstance(s, killclasses):
                s.kill()


def run():
    global curboard
    import boards
    from boards import curboard
    from player import BubPlayer

    for key, (filename, rect) in localmap.items():
        filename = os.path.join(os.path.dirname(__file__), filename)
        filename = os.path.abspath(filename)
        if filename.find('%d') >= 0:
            for p in BubPlayer.PlayerList:
                images.sprmap[key, p.pn] = (filename % p.pn, rect)
        else:
            images.sprmap[key] = (filename, rect)
    
    boards.replace_boardgen(Arkanoid().bgen())
