import sys


KeyPressed  = 2
KeyReleased = 3


class Display_X:
    sound = 0
    use_shm = 0
    
    def __init__(self, width, height, title):
        import xshm
        self.xdpy = xdpy = xshm.Display(width, height, self.use_shm)
        self.pixmap = xdpy.pixmap
        self.getppm = xdpy.getppm
        self.putppm = xdpy.putppm
        self.flip   = xdpy.flip
        self.close  = xdpy.close
        self.clear  = xdpy.clear
        self.keyevents = xdpy.keyevents
        self.mouseevents = xdpy.mouseevents
        self.pointermotion = xdpy.pointermotion
        if self.use_shm and not xdpy.shmmode():
            print >> sys.stderr, \
                  "Note: cannot use SHM extension (%dx%d), display will be slow." % \
                  (width, height)
        pixel = "\x00\x00\x80"
        hole  = "\x01\x01\x01"
        self.taskbkgnd = self.pixmap(32, 32,
                                     ((pixel+hole)*16 + (hole+pixel)*16) * 16,
                                     0x010101)

    def has_sound(self):
        return 0

    def selectlist(self):
        from socket import fromfd, AF_INET, SOCK_STREAM
        return [fromfd(self.xdpy.fd(), AF_INET, SOCK_STREAM)]

    def taskbar(self, (x, y, w, h)):
        for j in range(y, y+h, 32):
            for i in range(x, x+w, 32):
                self.putppm(i, j, self.taskbkgnd,
                            (0, 0, x+w-i, y+h-j))


class Display_SHM(Display_X):
    use_shm = 1


def Display_PYGAME(width, height, title):
    import pygameintf
    return pygameintf.Display(width, height, title)

def Display_PYXLIB(width, height, title):
    import pythonxlibintf
    return pythonxlibintf.Display(width, height, title)


def open_dpy(mode, width, height, title):
    dpyclass = globals().get('Display_' + mode.upper())
    if dpyclass is None:
        raise ValueError, mode
    return dpyclass(width, height, title)
