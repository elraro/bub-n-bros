#! /usr/bin/env python

from __future__ import generators
import sys, os, random

sys.path.append(os.path.join(os.pardir, 'common'))
import gamesrv, boards


# parse command-line
def usage():
  print >> sys.stderr, 'usage:'
  print >> sys.stderr, '  python bb.py [level-file.bin] [-b#] [-s#] [-l#] [-rxxx]'
  print >> sys.stderr, 'options:'
  print >> sys.stderr, '  -b#   start at board number # (default 1)'
  print >> sys.stderr, '  -s#   advance board number by steps of # (default 1)'
  print >> sys.stderr, '  -l#   limit the number of lives to #'
  print >> sys.stderr, '  -rxxx record the game in file xxx'
  print >> sys.stderr, '  -p#   set HTTP server port (default 8000, 0=disable)'
  sys.exit(1)
num = 0
gamesrv.FnHttpPort = 8000
for a in sys.argv[1:]:
  if a.startswith('-'):
    if a.startswith('-b'):
      num = max(0, int(a[2:]) - 1)
    elif a.startswith('-s'):
      boards.set_boardstep(int(a[2:]))
    elif a.startswith('-l'):
      boards.set_lives(int(a[2:]))
    elif a.startswith('-r'):
      gamesrv.RecordFile(a[2:])
    elif a.startswith('-p'):
      gamesrv.FnHttpPort = int(a[2:])
    else:
      print >> sys.stderr, 'unknown option', a
      usage()
  else:
    boards.set_levelfile(a)
boards.loadmodules(0)


def GetPlayers():
  from player import BubPlayer
  return dict(zip(range(len(BubPlayer.PlayerList)),
                  BubPlayer.PlayerList))

def kTimer():
  frametime = 0.0
  while frametime < 1.1:
    import boards
    for gen in boards.BoardGen[:]:
      try:
        frametime += gen.next()
      except StopIteration:
        try:
          boards.BoardGen.remove(gen)
        except ValueError:
          pass
  return frametime * boards.FRAME_TIME

def kExcHandler(kbd):
  from player import BubPlayer
  if kbd and not [p for p in BubPlayer.PlayerList if p.isplaying()]:
    return 0
  import traceback
  print "-"*60
  traceback.print_exc()
  print "-"*60
  import boards
  num = getattr(boards.curboard, 'num', 0)
  print "Correct the problem and leave pdb to restart board %d..." % num
  import pdb; pdb.post_mortem(sys.exc_info()[2])
  boards.loadmodules(1)
  import boards
  boards.curboard = None
  boards.BoardGen = [boards.next_board(num)]
  frametime = 20
  return 1

gamesrv.playfield.width = boards.bwidth + 9*boards.CELL
gamesrv.playfield.height = boards.bheight
gamesrv.playfield.backcolor = 0x000000

boards.BoardGen = [boards.next_board(num)]
del boards


keybmp = gamesrv.getbitmap(os.path.join('images', 'keys.ppm'))
def keybmplist(x):
  return [keybmp.geticon(x, y, 32, 32) for y in range(0, 128, 32)]

gamesrv.FnKeys = [
  ("right",  keybmplist(0),   "kRight"),
  ("left",   keybmplist(32),  "kLeft"),
  ("jump",   keybmplist(64),  "kJump"),
  ("fire",   keybmplist(96),  "kFire"),
  ("-right", [],              "kmRight"),
  ("-left",  [],              "kmLeft"),
  ("-jump",  [],              "kmJump"),
  ("-fire",  [],              "kmFire"),
  ]
gamesrv.FnDesc = "Bub & Bob"
gamesrv.FnPath = "bubbob/images/*.ppm:bubbob/music/*.wav"
gamesrv.FnBasePath = ["bubbob"]
gamesrv.FnPlayers = GetPlayers
gamesrv.FnFrame = kTimer
gamesrv.FnExcHandler = kExcHandler
gamesrv.Run()

#import profile
#prof = profile.Profile()
#try:
#  prof = prof.run('gamesrv.Run()')
#finally:
#  prof.dump_stats('profbb')
