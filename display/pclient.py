#! /usr/bin/env python

import sys, os
from socket import *
from select import select
import cStringIO, struct, zlib
import time
from common.msgstruct import *
from common import hostchooser
import modes
from modes import KeyPressed, KeyReleased

#import psyco; psyco.full()


def read(sock, count):
    buffer = ""
    while len(buffer) < count:
        t = sock.recv(count - len(buffer))
        if not t:
            raise error, "connexion closed"
        buffer += t
    return buffer


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


class Playfield:
    TASKBAR_HEIGHT = 48
    
    def __init__(self, sockaddr):
        print "connecting to %r..." % (sockaddr,)
        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.connect(sockaddr)
        self.sockaddr = sockaddr
        if read(self.s, len(MSG_WELCOME)) != MSG_WELCOME:
            raise error, "connected to something not a game server"
        line2 = ''
        while not line2.endswith('\n'):
            line2 += self.s.recv(1)

        self.gameident = line2.strip()
##        self.datapath = None
##        if self.gameident.endswith(']'):
##            i = self.gameident.rfind('[')
##            if i >= 0:
##                self.gameident, self.datapath = (self.gameident[:i].strip(),
##                                                 self.gameident[i+1:-1])
        print "connected to %r." % self.gameident

    def run(self, mode):
        self.playing = {}   # 0, 1, or 'l' for local
        self.keys = {}
        self.keycodes = {}
        self.dpy = None
        self.bitmaps = {}
        self.icons = {}
        self.sounds = {}
        self.musics = {}
        self.sprites = []
        self.playingsounds = {}
        self.playericons = {}
        self.screenmode = mode
        self.udpsock = None
        pss = hostchooser.serverside_ping()
        self.initial_iwtd = [self.s] + pss
        self.iwtd = self.initial_iwtd[:]
        inbuf = ""
        delay = 0.0
        while 1:
            if self.dpy:
                self.processkeys()
            iwtd, owtd, ewtd = select(self.iwtd, [], [], delay)
            delay = 0.5
            if self.dpy:
                self.processkeys()
            if self.s in iwtd:
                while self.s in iwtd:
                    inputdata = self.s.recv(0x6000)
                    ##import os; logfn='/tmp/log%d'%os.getpid()
                    ##g = open(logfn, 'ab'); g.write(inputdata); g.close()
                    inbuf += inputdata
                    while inbuf:
                        values, inbuf = decodemessage(inbuf)
                        if not values:
                            break  # incomplete message

                        #dump = list(values)
                        #for ii in range(len(dump)):
                        #    if isinstance(dump[ii], str) and len(dump[ii])>20:
                        #        dump[ii] = dump[ii][:15]+'....'
                        #print >> sys.stderr, dump

                        fn = Playfield.MESSAGES.get(values[0], self.msg_unknown)
                        fn(self, *values[1:])
                    iwtd, owtd, ewtd = select(self.iwtd, [], [], 0)
            if self.dpy:
                if self.udpsock in iwtd:
                    while self.udpsock in iwtd:
                        udpdata = self.udpsock.recv(65535)
                        iwtd, owtd, ewtd = select(self.iwtd, [], [], 0)
                        #if iwtd:
                        #    print "udp skip: %d bytes" % len(udpdata)
                    #print "udp recv: %d bytes" % len(udpdata)
                    self.update_sprites(udpdata)
                if self.taskbarmode:
                    self.taskbaranim = 0
                    self.flip_with_taskbar()
                    if self.taskbaranim:
                        delay = 0.04
                else:
                    self.dpy.flip()
            for sock in iwtd:
                if sock in pss:
                    hostchooser.answer_ping(sock, self.gameident, self.sockaddr)

    def update_sprites(self, udpdata):
        sprites = self.sprites
        unpack = struct.unpack

        currentsounds = {}
        base = 0
        while udpdata[base+4:base+6] == '\xFF\xFF':
            key, lvol, rvol = struct.unpack("!hBB", udpdata[base:base+4])
            try:
                snd = self.sounds[key]
            except KeyError:
                pass  # ignore sounds with bad code  (probably not defined yet)
            else:
                n = self.playingsounds.get(key)
                if n:
                    currentsounds[key] = n-1
                else:
                    self.dpy.play(snd,
                                  lvol / 255.0,
                                  rvol / 255.0)
                    currentsounds[key] = 4
            base += 6
        self.playingsounds = currentsounds
        
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

        t0, n = self.painttimes
        n = n + 1
        if n == 50:
            t = time.time()
            t, t0 = t-t0, t
            if t:
                print "%.2f images per second" % (float(n)/t)
            n = 0
        self.painttimes = t0, n

    def flip_with_taskbar(self, (cx,cy)=(-1,0)):
        clic_id = None
        y0 = self.height - self.TASKBAR_HEIGHT
        if cy < y0:
            cx = -1
        rect = (0, y0, self.width, self.TASKBAR_HEIGHT)
        bkgnd = self.dpy.getppm(rect)
        self.dpy.taskbar(rect)
        f = 1.5 * time.time()
        f = f-int(f)
        pi = self.playericons.items()
        pi.sort()
        xpos = 0
        for id, ico in pi:
            if self.playing.get(id) != 'l':
                w, h = ico.size
                xpos += int(w * 5 / 3)
                if not self.playing.get(id):
                    y = self.height - h
                    if xpos-w <= cx < xpos:
                        clic_id = id
                    if self.keydefinition and id == self.keydefinition[0]:
                        num, icons = self.keys[self.nextkeyname()]
                        ico = icons[int(f*len(icons))-1]
                        y = y0 + int((self.TASKBAR_HEIGHT-ico.size[1])/2)
                        self.taskbaranim = 1
                    self.dpy.putppm(xpos-w, y,
                                    ico.bitmap, ico.rect)
        pi.reverse()
        f = f * (1.0-f) * 4.0
        xpos = self.width
        for id, ico in pi:
            if self.playing.get(id) == 'l':
                w, h = ico.size
                xpos -= int(w * 5 / 3)
                dy = self.TASKBAR_HEIGHT - h - 1
                y = self.height - h - int(dy*f)
                if xpos <= cx < xpos+w:
                    clic_id = id
                self.dpy.putppm(xpos, y, ico.bitmap, ico.rect)
                self.taskbaranim = 1
        self.dpy.flip()
        self.dpy.putppm(0, y0, bkgnd)
        return clic_id

    def nextkeyname(self):
        pid, df = self.keydefinition
        undef = [(num, keyname) for keyname, (num, icons) in self.keys.items()
                 if not df.has_key(keyname) and icons]
        if undef:
            num, keyname = min(undef)
            return keyname
        else:
            return None

    def startplaying(self):
        self.udpsock = socket(AF_INET, SOCK_DGRAM)
        self.udpsock.bind(('', INADDR_ANY))
        host, port = self.udpsock.getsockname()
        self.s.sendall(message(CMSG_UDP_PORT, port))
        self.iwtd.append(self.udpsock)
        if self.dpy.has_sound():
            self.s.sendall(message(CMSG_ENABLE_MUSIC, 1))
            self.s.sendall(message(CMSG_PING))

        #for i in range(len(self.actions)):
        #    #for color in self.actions[i].get('players', []):
        #    #    self.s.sendall("\xFF" + message(CMSG_ADD_PLAYER, color))
        #    self.s.sendall(message(CMSG_ADD_PLAYER, i))

    def processkeys(self):
        keyevents = self.dpy.keyevents()
        if keyevents:
            pending = {}
            for keysym, event in keyevents:
                pending[keysym] = event
            for keysym, event in pending.items():
                code = self.keycodes.get((keysym, event))
                if code and self.playing.get(code[0]) == 'l':
                    self.s.sendall(code[1])
                elif self.keydefinition:
                    self.define_key(keysym)
        pointermotion = self.dpy.pointermotion()
        if pointermotion:
            x, y = pointermotion
            self.settaskbar(y >= self.height - self.TASKBAR_HEIGHT)
        mouseevents = self.dpy.mouseevents()
        if mouseevents:
            self.keydefinition = None
            for clic in mouseevents:
                clic_id = self.flip_with_taskbar(clic)
                if clic_id is not None:
                    if self.playing.get(clic_id) == 'l':
                        self.s.sendall(message(CMSG_REMOVE_PLAYER, clic_id))
                    else:
                        self.keydefinition = clic_id, {}

    def settaskbar(self, nmode):
        if self.taskbarfree:
            self.taskbarmode = (nmode or
                                'l' not in self.playing.values() or
                                (self.keydefinition is not None))

    def define_key(self, keysym):
        clic_id, df = self.keydefinition
        if keysym in df.values():
            return
        df[self.nextkeyname()] = keysym
        if self.nextkeyname() is not None:
            return
        self.keydefinition = None
        self.s.sendall(message(CMSG_ADD_PLAYER, clic_id))
        for keyname, (num, icons) in self.keys.items():
            if keyname[:1] == '-':
                event = KeyReleased
                keyname = keyname[1:]
            else:
                event = KeyPressed
            if df.has_key(keyname):
                keysym = df[keyname]
                self.keycodes[keysym, event] = \
                                      clic_id, message(CMSG_KEY, clic_id, num)

    def msg_unknown(self, *rest):
        print >> sys.stderr, "?"

    def msg_player_join(self, id, local, *rest):
        if local:
            self.playing[id] = 'l'
            self.settaskbar(0)
        else:
            self.playing[id] = 1

    def msg_player_kill(self, id, *rest):
        self.playing[id] = 0
        for key, (pid, msg) in self.keycodes.items():
            if pid == id:
                del self.keycodes[key]

    def msg_def_playfield(self, width, height, *rest):
        if self.dpy is not None:
            self.dpy.close()
        self.width = width
        self.height = height
        self.dpy = modes.open_dpy(self.screenmode, width, height, self.gameident)
##        if self.datapath and PARSE_FILES:
##            self.parsefiles()
        if self.dpy.has_sound():
            self.s.sendall(message(CMSG_ENABLE_SOUND))
        self.iwtd = self.dpy.selectlist() + self.initial_iwtd
        self.dpy.clear()   # backcolor is ignored
        self.painttimes = (time.time(), 0)
        self.s.sendall(message(CMSG_PING))
        self.taskbarmode = 0
        self.taskbarfree = 0
        self.taskbaranim = 0
        self.keydefinition = None

##    def parsefiles(self):
##        try:
##            import md5, glob
##        except ImportError:
##            return
##        cwd = os.getcwd()
##        try:
##            os.chdir(os.path.join(os.path.dirname(__file__), os.pardir))
##            for path in self.datapath.split(':'):
##                if path:
##                    for filename in glob.glob(path):
##                        #print filename
##                        chksum = md5.md5()
##                        f = open(filename, 'rb')
##                        while 1:
##                            data = f.read(65536)
##                            if not data: break
##                            chksum.update(data)
##                        del data
##                        f.close()
##                        self.s.sendall(message(CMSG_DEF_FILE, filename.lower(),
##                                               chksum.digest()))
##        finally:
##            os.chdir(cwd)

    def msg_def_key(self, name, num, *icons):
        self.keys[name] = num, [self.icons[ico] for ico in icons]

    def msg_def_icon(self, bmpcode, icocode, x, y, w, h, *rest):
        self.icons[icocode] = Icon(self.bitmaps[bmpcode], (x, y, w, h))
        #print >> sys.stderr, "def_icon  ", bmpcode, (x,y,w,h), '->', icocode

    def msg_def_bitmap(self, bmpcode, data, colorkey=None, *rest):
##        if isinstance(data, str):
        data = zlib.decompress(data)
##        else:
##            data = data.read()
        self.bitmaps[bmpcode] = loadpixmap(self.dpy, data, colorkey)
        #print >> sys.stderr, "def_bitmap", bmpcode

    def msg_def_sample(self, smpcode, data, *rest):
##        if isinstance(data, str):
        data = zlib.decompress(data)
##        else:
##            data = data.read()
        self.sounds[smpcode] = self.dpy.sound(data)

    def msg_def_music(self, code, position, data, *rest):
##        if isinstance(data, str):
##            pass
##        else:
##            data = data.read()
        try:
            m = self.musics[code]
        except KeyError:
            m = self.musics[code] = self.dpy.Music()
        m.write(position, data)

##    def msg_load_prefix(self, filename, dataindex, *rest):
##        basepath = os.path.join(os.path.dirname(__file__), os.pardir)
##        print basepath, filename
##        f = open(os.path.join(basepath, filename), 'rb')
##        rest = rest[:dataindex] + (f,) + rest[dataindex:]
##        self.MESSAGES[rest[0]](self, *rest[1:])
##        f.close()

    def msg_play_music(self, loop_from, *codes):
        self.dpy.play_musics([self.musics[c] for c in codes], loop_from)

    def msg_fadeout(self, time, *rest):
        self.dpy.fadeout(time)

    def msg_player_icon(self, pid, icocode, *rest):
        self.playericons[pid] = self.icons[icocode]

    def msg_ping(self, *rest):
        self.s.sendall(message(CMSG_PONG, *rest))

    def msg_pong(self, *rest):
        if self.udpsock is None:
            self.startplaying()
        elif self.dpy.has_sound():
            self.s.sendall(message(CMSG_ENABLE_MUSIC, 2))
        if not self.taskbarfree and not self.taskbarmode:
            self.taskbarfree = 1
            self.settaskbar(1)
    
    MESSAGES = {
        MSG_DEF_PLAYFIELD: msg_def_playfield,
        MSG_DEF_KEY      : msg_def_key,
        MSG_DEF_ICON     : msg_def_icon,
        MSG_DEF_BITMAP   : msg_def_bitmap,
        MSG_DEF_SAMPLE   : msg_def_sample,
        MSG_DEF_MUSIC    : msg_def_music,
        MSG_PLAY_MUSIC   : msg_play_music,
        MSG_FADEOUT      : msg_fadeout,
        MSG_PLAYER_JOIN  : msg_player_join,
        MSG_PLAYER_KILL  : msg_player_kill,
        MSG_PLAYER_ICON  : msg_player_icon,
        MSG_PING         : msg_ping,
        MSG_PONG         : msg_pong,
##        MSG_LOAD_PREFIX  : msg_load_prefix,
        }


def run(server, mode):
    Playfield(server).run(mode)

def usage():
    print >> sys.stderr, "usage:"
    print >> sys.stderr, "  python pclient.py [-X | -shm] [host:port]"
    sys.exit(2)

def main():
    mode = 'pygame'
    argv = sys.argv[1:]
    if argv and argv[0][:1] == '-':
        opt = argv[0].upper()
        if opt == '-X':
            mode = 'X'
        elif opt == '-SHM':
            mode = 'shm'
        else:
            usage()
        del argv[0]
    if len(argv) != 1:
        usage()
    hosts = argv[0].split(':')
    if len(hosts) != 2:
        usage()
    host, port = hosts
    try:
        port = int(port)
    except:
        usage()
    run((host, port), mode)

if __name__ == '__main__':
    main()
