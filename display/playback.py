#! /usr/bin/env python

import sys, os, gzip
from socket import *
from select import select
import cStringIO, struct, zlib
import time
from common.msgstruct import *
from common import hostchooser
import modes
from modes import KeyPressed, KeyReleased

#import psyco; psyco.full()


def loadpixmap(dpy, data, colorkey=None):
    f = cStringIO.StringIO(data)
    sig = f.readline().strip()
    assert sig == "P6"
    while 1:
        line = f.readline().strip()
        if not line.startswith('#'):
            break
    wh = line.split()
    w, h = map(int, wh)
    sig = f.readline().strip()
    assert sig == "255"
    data = f.read()
    f.close()
    if colorkey is None:
        colorkey = -1
    elif colorkey < 0:
        r, g, b = struct.unpack("BBB", self.data[:3])
        colorkey = b | (g<<8) | (r<<16)
    return dpy.pixmap(w, h, data, colorkey)

class Icon:
    def __init__(self, bitmap, (x, y, w, h)):
        self.rect = x, y, w, h
        self.size = w, h
        self.bitmap = bitmap


class Playback:
    gameident = 'Playback'
    
    def __init__(self, filename, mode='shm'):
        f = gzip.open(filename, 'rb')
        self.screenmode = mode
        self.width = None
        self.bitmaps = {}
        self.icons = {}
        self.frames = []
        inbuf = ''
        while 1:
            values, inbuf = decodemessage(inbuf)
            if not values:
                # incomplete message
                data = f.read(8192)
                if not data:
                    break
                inbuf += data
            else:
                fn = Playback.MESSAGES.get(values[0], self.msg_unknown)
                fn(self, *values[1:])
        print '%d frames in file.' % len(self.frames)
        f.close()
        assert self.width, "no playfield definition found in file"

        self.dpy = modes.open_dpy(self.screenmode,
                                  self.width, self.height, self.gameident)
        self.dpy.clear()   # backcolor is ignored
        self.sprites = []
        for bmpcode, (data, colorkey) in self.bitmaps.items():
            data = zlib.decompress(data)
            self.bitmaps[bmpcode] = loadpixmap(self.dpy, data, colorkey)
        for icocode, (bmpcode, rect) in self.icons.items():
            self.icons[icocode] = Icon(self.bitmaps[bmpcode], rect)
        self.go(0)

    def go(self, n):
        self.n = n
        self.update_sprites(self.frames[n])
        self.dpy.flip()

    def save(self, filename=None):
        "shm only!"
        w, h, data, reserved = self.dpy.getppm((0, 0, self.width, self.height))
        f = open(filename or ('frame%d.ppm' % self.n), 'wb')
        print >> f, 'P6'
        print >> f, w, h
        print >> f, 255
        for i in range(0, len(data), 4):
            f.write(data[i+2]+data[i+1]+data[i])
        f.close()

    def update_sprites(self, udpdata):
        sprites = self.sprites
        unpack = struct.unpack
        base = 0
        for j in range(len(sprites)):
            if sprites[j][0] != udpdata[base:base+6]:
                removes = sprites[j:]
                del sprites[j:]
                removes.reverse()
                eraser = self.dpy.putppm
                for reserved, eraseargs in removes:
                    eraser(*eraseargs)
                break
            base += 6
        getter = self.dpy.getppm
        setter = self.dpy.putppm
        #print "%d sprites redrawn" % (len(udpdata)/6-j)
        for j in range(base, len(udpdata)-5, 6):
            info = udpdata[j:j+6]
            x, y, icocode = unpack("!hhh", info[:6])
            try:
                ico = self.icons[icocode]
                sprites.append((info, (x, y, getter((x, y) + ico.size))))
                setter(x, y, ico.bitmap, ico.rect)
            except KeyError:
                #print "bad ico code", icocode
                pass  # ignore sprites with bad ico (probably not defined yet)

    def msg_unknown(self, *rest):
        pass

    def msg_def_playfield(self, width, height, *rest):
        self.width, self.height = width, height

    def msg_def_icon(self, bmpcode, icocode, x, y, w, h, *rest):
        self.icons[icocode] = bmpcode, (x, y, w, h)

    def msg_def_bitmap(self, bmpcode, data, colorkey=None, *rest):
        self.bitmaps[bmpcode] = data, colorkey

    def msg_recorded(self, data):
        self.frames.append(data)

    MESSAGES = {
        MSG_DEF_PLAYFIELD: msg_def_playfield,
        MSG_DEF_ICON     : msg_def_icon,
        MSG_DEF_BITMAP   : msg_def_bitmap,
        MSG_RECORDED     : msg_recorded,
        }
