
 ################################################
##     pygame-based implementation of xshm     ##
################################################

import os
import pygame
from pygame.locals import *

ENDMUSICEVENT = USEREVENT


KeyPressed  = 2
KeyReleased = 3


def maybe_unlink(file):
    try:
        os.unlink(file)
    except:
        pass


class Display:
    
    def __init__(self, width, height, title):
        # Initialize pygame
        pygame.init()

        # Set the display mode
        winstyle = 0  # |FULLSCREEN
        bestdepth = pygame.display.mode_ok((width, height), winstyle, 32)
        self.screen = pygame.display.set_mode((width, height),
                                              winstyle, bestdepth)
        self.offscreen = pygame.Surface((width, height))
        #decorate the game window
        pygame.display.set_caption(title)
        #pygame.mouse.set_visible(0)
        self.tbcache = None, None
        self.events_key = []
        self.events_mouse = []
        self.prevposition = None

    def pixmap(self, w, h, data, colorkey=-1):
        img = pygame.image.fromstring(data, (w, h), "RGB")
        if colorkey >= 0:
            r = colorkey & 0xFF
            g = (colorkey >> 8) & 0xFF
            b = (colorkey >> 16) & 0xFF
            img.set_colorkey([r, g, b], RLEACCEL)
        return img

##    def vflipppm(self, img):
##        w, h = img.get_size()
##        colorkey = img.get_colorkey()
##        data = pygame.image.tostring(img, "RGB", 1)
##        flipimg = pygame.image.fromstring(data, (w, h), "RGB")
##        flipimg.set_colorkey(colorkey, RLEACCEL)
##        return flipimg, h

    def getppm(self, rect, bkgnd=None):
        if bkgnd is None:
            bkgnd = pygame.Surface(rect[2:])
        bkgnd.blit(self.offscreen, (0, 0), Rect(rect))
        return bkgnd

    def putppm(self, x, y, bitmap, rect=None):
        if rect:
            self.offscreen.blit(bitmap, (x, y), rect)
        else:
            self.offscreen.blit(bitmap, (x, y))

    def flip(self):
        if pygame.event.get([QUIT]):
            raise SystemExit
        self.screen.blit(self.offscreen, (0, 0))
        pygame.display.flip()

    def close(self):
        pygame.display.quit()

    def clear(self):
        self.offscreen.fill([0,0,0,])

    def events_poll(self):
        while 1:
            e = pygame.event.poll()
            if e.type == NOEVENT:
                break
            elif e.type == KEYDOWN:
                self.events_key.append((e.key, KeyPressed))
                del self.events_key[:-16]
            elif e.type == KEYUP:
                self.events_key.append((e.key, KeyReleased))
                del self.events_key[:-16]
            elif e.type == MOUSEBUTTONDOWN:
                self.events_mouse.append(e.pos)
                del self.events_mouse[:-8]
            elif e.type == ENDMUSICEVENT:
                self.next_music()
            elif e.type == QUIT:
                raise SystemExit

    def keyevents(self):
        self.events_poll()
        events = self.events_key
        self.events_key = []
        return events

    def pointermotion(self):
        position = pygame.mouse.get_pos()
        if position != self.prevposition:
            self.prevposition = position
            return position
        else:
            return None

    def mouseevents(self):
        self.events_poll()
        events = self.events_mouse
        self.events_mouse = []
        return events

    def has_sound(self):
        if pygame.mixer:
            try:
                pygame.mixer.init()
            except pygame.error:
                return 0
            else:
                return 1
        else:
            return 0

    def selectlist(self):
        return []

    def sound(self, data, fileext='.wav'):
        import tempfile
        file = tempfile.mktemp(fileext)
        try:
            f = open(file, 'wb')
            f.write(data)
            f.close()
            return pygame.mixer.Sound(file)
        finally:
            maybe_unlink(file)

    def play(self, sound, lvolume, rvolume):
        channel = pygame.mixer.find_channel(1)
        channel.stop()
        try:
            channel.set_volume(lvolume, rvolume)
        except TypeError:
            channel.set_volume(0.5 * (lvolume+rvolume))
        channel.play(sound)

    def taskbar(self, (x, y, w, h)):
        tbs, tbh = self.tbcache
        if tbh != h:
            tbs = pygame.Surface((32, h)).convert_alpha()
            alpha_f = 256.0 / h
            for j in range(h):
                tbs.fill((128, 128, 255, int(j*alpha_f)),
                         (0, j, 32, 1))
            self.tbcache = tbs, h
        for i in range(x, x+w, 32):
            dw = x+w-i
            if dw < 32:
                self.offscreen.blit(tbs, (i, y), (0, 0, dw, h))
            else:
                self.offscreen.blit(tbs, (i, y))


    class Music:
        def __init__(self, fileext='.wav'):
            import atexit, tempfile
            self.file = tempfile.mktemp(fileext)
            atexit.register(maybe_unlink, self.file)
            self.f = open(self.file, 'wb')
        def write(self, position, data):
            #print "write:", self.file, '|', position, '->', position+len(data)
            self.f.seek(position)
            self.f.write(data)
            self.f.flush()

    def play_musics(self, musics, loop_from):
        self.cmusics = musics, loop_from, 0
        pygame.mixer.music.set_endevent(ENDMUSICEVENT)
        self.next_music()

    def next_music(self):
        musics, loop_from, c = self.cmusics
        if c >= len(musics):  # end
            c = loop_from
            if c >= len(musics):
                pygame.mixer.music.stop()
                return
        pygame.mixer.music.load(musics[c].file)
        pygame.mixer.music.play()
        self.cmusics = musics, loop_from, c+1

    def fadeout(self, millisec):
        #print "fadeout:", millisec
        pygame.mixer.music.fadeout(millisec)
