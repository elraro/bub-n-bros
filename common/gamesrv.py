from socket import *
from select import select
from struct import pack, unpack
import zlib, os
from time import time
from msgstruct import *
import hostchooser

EWOULDBLOCK = (11,     # Posix
               10035)  # Windows


class Icon:
  count = 0

  def __init__(self, bmpcode, code, x,y,w,h):
    self.w = w
    self.h = h
    self.code = code
    self.msgdef = message(MSG_DEF_ICON, bmpcode, code, x,y,w,h)
    framemsgappend(self.msgdef)
    #print "Icon(%d, %d, %d,%d,%d,%d)" % (bmpcode, code, x,y,w,h)


class Bitmap:

  def __init__(self, code, filename, colorkey=None):
    self.code = code
    self.filename = filename
    self.icons = {}
    data = zlib.compress(self.read())
    if colorkey is not None:
      self.msgdef = message(MSG_DEF_BITMAP, code, data, colorkey)
    else:
      self.msgdef = message(MSG_DEF_BITMAP, code, data)
    framemsgappend(self.msgdef)

  def read(self):
    f = open(self.filename, "rb")
    data = f.read()
    f.close()
    return data

  def geticon(self, x,y,w,h):
    rect = (x,y,w,h)
    try:
      return self.icons[rect]
    except:
      ico = Icon(self.code, Icon.count, x,y,w,h)
      Icon.count += 1
      self.icons[rect] = ico
      return ico

  def geticonlist(self, w, h, count):
    return map(lambda i, fn=self.geticon, w=w, h=h: fn(i*w, 0, w, h), range(count))

  def defall(self):
    return [self.msgdef] + [i.msgdef for i in self.icons.values()]


class MemoryBitmap(Bitmap):
  
  def __init__(self, code, data, colorkey=None):
    self.data = data
    Bitmap.__init__(self, code, None, colorkey)

  def read(self):
    return self.data


class Sample:

  def __init__(self, code, filename, freqfactor=1):
    self.code = code
    self.filename = filename
    self.freqfactor = freqfactor
    data = zlib.compress(self.read())
    self.msgdef = message(MSG_DEF_SAMPLE, code, data)
    sndframemsgappend(self.msgdef)

  def read(self):
    f = open(self.filename, "rb")
    data = f.read()
    f.close()
    if self.freqfactor != 1:
      freq, = unpack("<i", data[24:28])
      freq = int(freq * self.freqfactor)
      data = data[:24] + struct.pack("<i", freq) + data[28:]
    return data

  def play(self, lvolume=1.0, rvolume=None, pad=0.5, singleclient=None):
    if rvolume is None:
      rvolume = lvolume
    lvolume *= 2.0*(1.0-pad)
    rvolume *= 2.0*pad
    if lvolume < 0.0:
      lvolume = 0.0
    elif lvolume > 1.0:
      lvolume = 1.0
    if rvolume < 0.0:
      rvolume = 0.0
    elif rvolume > 1.0:
      rvolume = 1.0
    message = pack("!hBBh", self.code, lvolume*255.0, rvolume*255.0, -1)
    if singleclient is None:
      clist = clients[:]
    else:
      clist = [singleclient]
    for c in clist:
      if c.sounds is not None:
        c.sounds.setdefault(message, 4)

  def defall(self):
    return [self.msgdef]


class Music:

  def __init__(self, code, filename, filerate=44100):
    self.code = code
    self.filename = filename
    self.filerate = filerate
    self.f = open(filename, 'rb')
    self.f.seek(0, 2)
    filesize = self.f.tell()
    self.endpos = max(self.filerate, filesize - self.filerate)

  def msgblock(self, position, limited=1):
    blocksize = self.filerate
    if limited and position+blocksize > self.endpos:
      blocksize = self.endpos-position
      if blocksize <= 0:
        return ''
    self.f.seek(position)
    return message(MSG_DEF_MUSIC, self.code, position, self.f.read(blocksize))

  def clientsend(self, clientpos):
    msg = self.msgblock(clientpos)
    #print 'clientsend:', self.code, len(msg), clientpos
    if msg:
      return [msg], clientpos + self.filerate
    else:
      return [], None

  def initialsend(self, c):
    return [self.msgblock(0), self.msgblock(self.endpos, 0)], self.filerate

  def defall(self):
    return []


def clearsprites():
  sprites_by_n.clear()
  sprites[:] = ['']

def compactsprites(insert_new=None, insert_before=None):
  global sprites, sprites_by_n
  if insert_before is not None:
    if insert_new.alive:
      insert_before = insert_before.alive
    else:
      insert_before = None
  newsprites = ['']
  newd = {}
  l = sprites_by_n.items()
  l.sort()
  for n, s in l:
    if n == insert_before:
      prevn = insert_new.alive
      newn = insert_new.alive = len(newsprites)
      newsprites.append(sprites[prevn])
      newd[newn] = insert_new
      l.remove((prevn, insert_new))
    newn = s.alive = len(newsprites)
    newsprites.append(sprites[n])
    newd[newn] = s
  sprites = newsprites
  sprites_by_n = newd


class Sprite:

  def __init__(self, ico, x,y):
    self.x = x
    self.y = y
    self.ico = ico
    self.alive = len(sprites)
    if (-ico.w < x < playfield.width and
        -ico.h < y < playfield.height):
      sprites.append(pack("!hhh", x, y, ico.code))
    else:
      sprites.append('')  # starts off-screen
    sprites_by_n[self.alive] = self

  def move(self, x,y, ico=None):
    self.x = x
    self.y = y
    if ico is not None:
      self.ico = ico
    sprites[self.alive] = pack("!hhh", x, y, self.ico.code)

  def step(self, dx,dy):
    x = self.x = self.x + dx
    y = self.y = self.y + dy
    sprites[self.alive] = pack("!hhh", x, y, self.ico.code)

  def seticon(self, ico):
    self.ico = ico
    sprites[self.alive] = pack("!hhh", self.x, self.y, ico.code)

  def hide(self):
    sprites[self.alive] = ''

  def kill(self):
    if self.alive:
      del sprites_by_n[self.alive]
      sprites[self.alive] = ''
      self.alive = 0

  def to_front(self):
    if self.alive and self.alive < len(sprites)-1:
      info = sprites[self.alive]
      sprites[self.alive] = ''
      del sprites_by_n[self.alive]
      self.alive = len(sprites)
      sprites_by_n[self.alive] = self
      sprites.append(info)

  def to_back(self, limit=None):
    assert self is not limit
    if limit:
      n1 = limit.alive + 1
    else:
      n1 = 1
    if self.alive > n1:
      if n1 in sprites_by_n:
        keys = sprites_by_n.keys()
        keys.remove(self.alive)
        keys.sort()
        keys = keys[keys.index(n1):]
        for n in keys:
          sprites_by_n[n].to_front()
        assert n1 not in sprites_by_n
      info = sprites[self.alive]
      sprites[self.alive] = ''
      del sprites_by_n[self.alive]
      self.alive = n1
      sprites_by_n[n1] = self
      sprites[n1] = info

  def __repr__(self):
    if self.alive:
      return "<sprite %d at %d,%d>" % (self.alive, self.x, self.y)
    else:
      return "<killed sprite>"


class Player:
  standardplayericon = None

  def playerjoin(self):
    pass

  def playerleaves(self):
    pass

  def _playerleaves(self):
    if self.isplaying():
      self._client.killplayer(self)
      del self._client
    self.playerleaves()

  def isplaying(self):
    return hasattr(self, "_client")


def deffieldmsg():
  msg = message(MSG_DEF_PLAYFIELD,
                playfield.width, playfield.height, playfield.backcolor)
  if not clients:
    framemsgappend(msg)  # for recording
  return msg


class Client:
  SEND_BOUND_PER_FRAME = 0x6000   # bytes
  KEEP_ALIVE           = 2.2      # seconds

  def __init__(self, socket, addr):
    socket.setblocking(0)
    self.socket = socket
    self.addr = addr
    self.udpsocket = None
##    if FnPath:
##      desc = '%s [%s]' % (FnDesc, FnPath)
##    else:
##      desc = FnDesc
    self.initialdata = MSG_WELCOME + FnDesc + '\n' + deffieldmsg()
    self.initialized = 0
    self.msgl = [message(MSG_PING)]
##    self.known_files = { }
    self.players = { }
    self.sounds = None
    self.has_music = 0
    self.activity = time()
    self.musicpos = { }
    for b in bitmaps.values():
      self.msgl += b.defall()
    for c in clients:
      for id in c.players.keys():
        self.msgl.append(message(MSG_PLAYER_JOIN, id, 0))
    self.finishinit()
    for id, p in FnPlayers().items():
      if p.standardplayericon is not None:
        self.msgl.append(message(MSG_PLAYER_ICON, id, p.standardplayericon.code))

  def emit(self, udpdata, now):
    buffer = self.initialdata
    if not buffer and self.initialized:
      buffer = ''.join(self.msgl)
    if buffer:
      try:
        count = self.socket.send(buffer[:self.SEND_BOUND_PER_FRAME])
      except error, e:
        if e.args[0] not in EWOULDBLOCK:
          self.disconnect(e, 'emit')
          return
      else:
        #g = open('log', 'ab'); g.write(buffer[:count]); g.close()
        buffer = buffer[count:]
        self.activity = now
      if self.initialdata:
        self.initialdata = buffer
      elif buffer:
        self.msgl = [buffer]
      else:
        self.msgl = []
    elif abs(now - self.activity) > self.KEEP_ALIVE:
      self.msgl.append(message(MSG_PING))
    if self.udpsocket is not None:
      #print "udp send: %d bytes" % len(udpdata)
      if self.sounds:
        udpdata = ''.join(self.sounds.keys() + [udpdata])
        for key, value in self.sounds.items():
          if value:
            self.sounds[key] = value-1
          else:
            del self.sounds[key]
      try:
        self.udpsocket.send(udpdata)
      except error:
        pass  # ignore UDP send errors (buffer full, etc.)
    if self.has_music > 1 and now >= self.musicstreamer:
      self.musicstreamer += 0.99
      self.sendmusicdata()

  def init(self):
    self.buf = ""
    return 1

  def receive(self, data):
    #print "receive:", `data`
    data = self.buf + data
    while data:
      values, data = decodemessage(data)
      if not values:
        break  # incomplete message
      fn = self.MESSAGES.get(values[0])
      if fn:
        fn(self, *values[1:])
      else:
        print "unknown message from", self.addr, ":", values
    self.buf = data

  def disconnect(self, err=None, infn=None):
    if err:
      extra = ": " + str(err)
    else:
      extra = ""
    if infn:
      extra += " in " + infn
    print 'Disconnected by', self.addr, extra
    for p in self.players.values():
      p._playerleaves()
    clients.remove(self)
    try:
      self.socket.close()
    except:
      pass
    if not clients:
      FnDisconnected()

  def killplayer(self, player):
    for id, p in self.players.items():
      if p is player:
        framemsgappend(message(MSG_PLAYER_KILL, id))
        del self.players[id]

  def joinplayer(self, id, *rest):
    if self.players.has_key(id):
      print "Note: player %s is already playing" % (self.addr+(id,),)
      return
    p = FnPlayers()[id]
    if p is None:
      print "Too many players. New player %s refused." % (self.addr+(id,),)
      self.msgl.append(message(MSG_PLAYER_KILL, id))
    elif p.isplaying():
      print "Note: player %s is already played by another client" % (self.addr+(id,),)
    else:
      print "New player %s" % (self.addr+(id,),)
      p._client = self
      p.playerjoin()
      self.players[id] = p
      framemsgappend(message(MSG_PLAYER_JOIN, id, 0))
      self.msgl.append(message(MSG_PLAYER_JOIN, id, 1))

  def remove_player(self, id, *rest):
    try:
      p = self.players[id]
    except KeyError:
      print "Note: player %s is not playing" % (self.addr+(id,),)
    else:
      p._playerleaves()

  def set_udp_port(self, port, *rest):
    self.udpsocket = socket(AF_INET, SOCK_DGRAM)
    self.udpsocket.setblocking(0)
    self.udpsocket.connect((self.addr[0], port))

  def enable_sound(self, *rest):
    self.sounds = {}
    for snd in samples.values():
      self.msgl += snd.defall()

  def enable_music(self, mode, *rest):
    self.has_music = mode
    self.startmusic()

  def startmusic(self):
    if self.has_music:
      self.musicstreamer = time()
      for cde in currentmusics[1:]:
        if cde not in self.musicpos:
          msgl, self.musicpos[cde] = music_by_id[cde].initialsend(self)
          self.msgl += msgl
      if self.has_music > 1:
        self.sendmusicdata()
        self.msgl.append(message(MSG_PLAY_MUSIC, *currentmusics))

  def sendmusicdata(self):
    for cde in currentmusics[1:]:
      if self.musicpos[cde] is not None:
        msgl, self.musicpos[cde] = music_by_id[cde].clientsend(self.musicpos[cde])
        self.msgl += msgl
        return

  def ping(self, *rest):
    self.initialized = 1
    self.msgl.append(message(MSG_PONG, *rest))

  def finishinit(self):
    pass

  def pong(self, *rest):
    pass

##  def def_file(self, filename, md5sum):
##    fnp = []
##    while filename:
##      filename, tail = os.path.split(filename)
##      fnp.insert(0, tail)
##    if fnp[:len(FnBasePath)] == FnBasePath:
##      filename = os.path.join(*fnp[len(FnBasePath):])
##      self.known_files[filename] = md5sum

  MESSAGES = {
    CMSG_ADD_PLAYER   : joinplayer,
    CMSG_REMOVE_PLAYER: remove_player,
    CMSG_UDP_PORT     : set_udp_port,
    CMSG_ENABLE_SOUND : enable_sound,
    CMSG_ENABLE_MUSIC : enable_music,
    CMSG_PING         : ping,
    CMSG_PONG         : pong,
##    CMSG_DEF_FILE     : def_file,
    }


class SimpleClient(Client):

  def finishinit(self):
    num = 0
    for keyname, icolist, fn in FnKeys:
      self.msgl.append(message(MSG_DEF_KEY, keyname, num,
                               *[ico.code for ico in icolist]))
      num += 1
  
  def cmsg_key(self, pid, keynum):
    try:
      player = self.players[pid]
      fn = FnKeys[keynum][2]
    except (KeyError, IndexError):
      FnUnknown()
    else:
      getattr(player, fn) ()

  MESSAGES = Client.MESSAGES.copy()
  MESSAGES.update({
    CMSG_KEY: cmsg_key,
    })


class playfield:
  width     = 640
  height    = 480
  backcolor = 0xFFFFFF


FnDesc    = "NoName"
FnPath    = None
FnBasePath= []
FnFrame   = lambda:1.0
FnClient  = SimpleClient
FnUnknown = lambda:None
FnExcHandler=lambda k: 0
FnPlayers = lambda:{}
FnKeys    = []
FnHttpPort= None

MAX_CLIENTS = 32

clients = []
bitmaps = {}
samples = {}
music_by_id = {}
currentmusics = [0]
sprites = ['']
sprites_by_n = {}
recording = None

def framemsgappend(msg):
  for c in clients:
    c.msgl.append(msg)
  if recording:
    recording[0].write(msg)

def sndframemsgappend(msg):
  for c in clients:
    if c.sounds is not None:
      c.msgl.append(msg)

def set_udp_port(port):
  hostchooser.UDP_PORT = port

def has_loop_music():
  return currentmusics[0] < len(currentmusics)-1

def set_musics(musics_intro, musics_loop, reset=1):
  mlist = []
  loop_from = len(musics_intro)
  mlist.append(loop_from)
  for m in musics_intro + musics_loop:
    mlist.append(m.code)
  if reset or mlist != currentmusics:
    currentmusics[:] = mlist
    for c in clients:
      c.startmusic()

def fadeout(time=1.0):
  sndframemsgappend(message(MSG_FADEOUT, int(time*1000)))
  currentmusics[:] = [0]


def getbitmap(filename, colorkey=None):
  try:
    return bitmaps[filename]
  except:
    bmp = Bitmap(len(bitmaps), filename, colorkey)
    bitmaps[filename] = bmp
    return bmp

def getsample(filename, freqfactor=1):
  try:
    return samples[filename, freqfactor]
  except:
    snd = Sample(len(samples), filename, freqfactor)
    samples[filename, freqfactor] = snd
    return snd

def getmusic(filename, filerate=44100):
  try:
    return samples[filename]
  except:
    mus = Music(len(samples), filename, filerate)
    samples[filename] = mus
    music_by_id[mus.code] = mus
    return mus

def newbitmap(data, colorkey=None):
  bmp = MemoryBitmap(len(bitmaps), data, colorkey)
  bitmaps[bmp] = bmp
  return bmp


def FnReady():
  import sys
  if hasattr(sys, 'AUTO_RUN'):
    import os
    os.system('start ' + sys.AUTO_RUN)

def FnDisconnected():
  import sys
  if hasattr(sys, 'AUTO_RUN'):
    raise SystemExit

def RecordFile(filename, sampling=1.0 / 10):
  import gzip, atexit
  global recording
  f = gzip.open(filename, 'wb')
  atexit.register(f.close)
  recording = [f, sampling, time() + sampling]

def recordudpdata(now, udpdata):
  recfile, recsampling, recnext = recording
  while now >= recnext:
    recnext += recsampling
  recording[2] = recnext
  recfile.write(message(MSG_RECORDED, udpdata))


def Run():

  s = socket(AF_INET, SOCK_STREAM)
  try:
    s.listen(1)
  except error:
    for PORT in range(12345, 12355):
      try:
        s.bind(('', PORT))
        s.listen(1)
      except error:
        pass
      else:
        break
    else:
      print "Server cannot find a free TCP socket port."
      return
  HOST, PORT = s.getsockname()
  FnReady()
  pss = hostchooser.serverside_ping()

  extramsg = ''
  if FnHttpPort:
    import javaserver
    if javaserver.setup(httpport=FnHttpPort, title=FnDesc, gameport=PORT,
                        width=playfield.width, height=playfield.height):
      extramsg = ', HTTP %d' % FnHttpPort

  print '%s server at %s:%d, UDP %d%s' % (FnDesc, gethostname(), PORT,
                                          hostchooser.UDP_PORT, extramsg)
  nextframe = time()

  try:
    while 1:
      try:
        now = time()
        delay = nextframe - now
        if delay<=0.0:
          nextframe = nextframe + FnFrame()
          sprites[0] = ''
          udpdata = ''.join(sprites)
          for c in clients[:]:
            c.emit(udpdata, now)
          now = time()
          if recording and now >= recording[2]:
            recordudpdata(now, udpdata)
          delay = nextframe - now
          if delay<0.0:
            nextframe = now
            delay = 0.0
        
        iwtd = [s] + [c.socket for c in clients] + pss
        iwtd, owtd, ewtd = select(iwtd, [], iwtd, delay)
        if ewtd:
          for c in clients[:]:
            if c.socket in ewtd:
              c.disconnect("error", "select")
          if s in ewtd:
            print "Error reported on listening socket"
        if iwtd:
          for c in clients[:]:
            if c.socket in iwtd:
              try:
                data = c.socket.recv(2048)
              except error, e:
                c.disconnect(e, "socket.recv")
              else:
                if data:
                  c.activity = now
                  c.receive(data)
          if s in iwtd:
            conn, addr = s.accept()
            if len(clients)==MAX_CLIENTS:
              print "Too many connections; refusing new connection from", addr
              conn.close()
            else:
              print 'Connected by', addr
              c = FnClient(conn, addr)
              if c.init():
                clients.append(c)
              else:
                print 'Connection refused.'
                conn.close()
          for sock in pss:
            if sock in iwtd:
              hostchooser.answer_ping(sock, FnDesc, ('', PORT))
      except KeyboardInterrupt:
        if not FnExcHandler(1):
          raise
      except:
        if not FnExcHandler(0):
          raise
  finally:
    s.close()
    if clients:
      print "Server crash -- waiting for clients to terminate..."
      while clients:
        iwtd = [c.socket for c in clients]
        iwtd, owtd, ewtd = select(iwtd, [], iwtd)
        for c in clients[:]:
          if c.socket in ewtd:
            c.disconnect("select reported an error")
          elif c.socket in iwtd:
            try:
              data = c.socket.recv(2048)
            except error, e:
              c.disconnect(e)
            else:
              if not data:
                c.disconnect("end of data")
    print "Server closed."
