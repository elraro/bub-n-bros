#! /usr/bin/env python

from __future__ import generators
import sys, os, random

if __name__ == '__main__':
    LOCALDIR = sys.argv[0]
else:
    LOCALDIR = __file__
LOCALDIR = os.path.abspath(os.path.dirname(LOCALDIR))

sys.path.append(os.path.abspath(os.path.join(LOCALDIR, os.pardir, 'common')))
import gamesrv

PROFILE = 0


class BubBobGame(gamesrv.Game):

    FnDesc = "Bub & Bob"
    FnBasePath = "bubbob"

    def __init__(self, levelfile,
                 beginboard  = 1,
                 stepboard   = 1,
                 limitlives  = None,
                 extralife   = 50000):
        gamesrv.Game.__init__(self)
        self.levelfile  = levelfile
        self.beginboard = beginboard
        self.stepboard  = stepboard
        self.limitlives = limitlives
        self.extralife  = extralife
        levelsname, ext = os.path.splitext(os.path.basename(levelfile))
        self.FnDesc     = BubBobGame.FnDesc + ' ' + levelsname
        self.openboard()
        self.openserver()

    def openboard(self, num=None):
        if num is None:
            num = self.beginboard-1
        import boards
        boards.loadmodules(force=1)
        import boards   # possibly re-import
        self.width = boards.bwidth + 9*boards.CELL
        self.height = boards.bheight
        boards.curboard = None
        boards.BoardGen = [boards.next_board(num)]

    def FnPlayers(self):
        from player import BubPlayer
        return dict(zip(range(len(BubPlayer.PlayerList)),
                        BubPlayer.PlayerList))

    def FnFrame(self):
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

    def FnExcHandler(self, kbd):
        from player import BubPlayer
        if kbd and not [p for p in BubPlayer.PlayerList if p.isplaying()]:
            return 0
        import traceback
        print "-"*60
        traceback.print_exc()
        print "-"*60
        import boards
        num = getattr(boards.curboard, 'num', None)
        print "Correct the problem and leave pdb to restart board %s..." % num
        import pdb; pdb.post_mortem(sys.exc_info()[2])
        self.openboard(num)
        return 1

    def FnListBoards():
        import boards
        result = []
        for fn in os.listdir('levels'):
            base, ext = os.path.splitext(fn)
            if ext in ('.py', '.bin'):
                result.append((base, os.path.join('levels', fn)))
        return result
    FnListBoards = staticmethod(FnListBoards)

    def FnExtraDesc(self):
        import boards
        s = gamesrv.Game.FnExtraDesc(self)
        if boards.curboard:
            s = 'board %d with %s' % (boards.curboard.num+1, s)
        return s


def setuphttp2path():
    dir = os.path.abspath(os.path.join(LOCALDIR, os.pardir, 'http2'))
    if not os.path.isdir(dir):
        print >> sys.stderr, '../http2: directory not found ("cvs update -d" ?)'
        sys.exit(1)
    sys.path.append(dir)

def parse_cmdline(argv):
    # parse command-line
    def usage():
        print >> sys.stderr, 'usage:'
        print >> sys.stderr, '  python bb.py [-w/--webbrowser=no]'
        print >> sys.stderr, 'where:'
        print >> sys.stderr, '  -w  --webbrowser=no  don''t automatically start web browser'
        print >> sys.stderr, 'or:'
        print >> sys.stderr, '  python bb.py [level-file.bin] [-m] [-b#] [-s#] [-l#]'
        print >> sys.stderr, 'with options:'
        print >> sys.stderr, '  -m  --metaserver  register the server on the Metaserver so anyone can join'
        print >> sys.stderr, '  -b#  --begin #    start at board number # (default 1)'
        print >> sys.stderr, '       --start #    synonym for --begin'
        print >> sys.stderr, '  -s#  --step #     advance board number by steps of # (default 1)'
        print >> sys.stderr, '  -l#  --lives #    limit the number of lives to #'
        print >> sys.stderr, '  -h   --help       display this text'
        #print >> sys.stderr, '  -rxxx record the game in file xxx'
        sys.exit(1)

    try:
        from getopt import gnu_getopt as getopt
    except ImportError:
        from getopt import getopt
    from getopt import error
    try:
        opts, args = getopt(argv, 'wmb:s:l:h',
                            ['webbrowser=', 'metaserver', 'start=', 'step=', 'lives=', 'help'])
    except error, e:
        print >> sys.stderr, 'bb.py: %s' % str(e)
        print >> sys.stderr
        usage()
        
    options = {}
    metaserver = 0
    webbrowser = 1
    for key, value in opts:
        if key in ('-w', '--webbrowser'):
            webbrowser = value.startswith('y')
        elif key in ('-m', '--metaserver'):
            metaserver = 1
        elif key in ('-b', '--start', '--begin'):
            options['beginboard'] = int(value)
        elif key in ('-s', '--step'):
            options['stepboard'] = int(value)
        elif key in ('-l', '--lives'):
            options['limitlives'] = int(value)
        elif key in ('-h', '--help'):
            usage()
    if args:
        if len(args) > 1:
            print >> sys.stderr, 'bb12.py: multiple level files specified'
            sys.exit(1)
        levelfile = os.path.abspath(args[0])
        os.chdir(LOCALDIR)
        BubBobGame(levelfile, **options)
        if metaserver:
            setuphttp2path()
            import httppages
            httppages.meta_register()
    else:
        os.chdir(LOCALDIR)
        if options:
            print >> sys.stderr, 'bb12.py: command-line options ignored'
        setuphttp2path()
        import httppages
        httppages.main(BubBobGame, webbrowser)


def setup():
    keybmp = gamesrv.getbitmap(os.path.join('images', 'keys.ppm'))
    def keybmplist(x):
        return [keybmp.geticon(x, y, 32, 32) for y in range(0, 128, 32)]
    BubBobGame.FnKeys = [
        ("right",  keybmplist(0),   "kRight"),
        ("left",   keybmplist(32),  "kLeft"),
        ("jump",   keybmplist(64),  "kJump"),
        ("fire",   keybmplist(96),  "kFire"),
        ("-right", [],              "kmRight"),
        ("-left",  [],              "kmLeft"),
        ("-jump",  [],              "kmJump"),
        ("-fire",  [],              "kmFire"),
        ]

setup()

def main():
    parse_cmdline(sys.argv[1:])
    if not PROFILE:
        gamesrv.mainloop()
    else:
        import profile
        prof = profile.Profile()
        try:
            prof = prof.run('gamesrv.mainloop()')
        finally:
            prof.dump_stats('profbb')

if __name__ == '__main__':
    main()
