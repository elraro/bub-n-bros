class FiledStderr:
    def __init__(self, fprev, filename):
        self._fprev = fprev
        self._filename = filename
        self._f = None
    def _open(self):
        if self._f is None:
            try:
                self._f = open(self._filename, 'a')
            except IOError:
                return 0
            print >> self._f, '='*60
        return 1
    def write(self, data):
        if self._open():
            self._f.write(data)
        self._fprev.write(data)
    def writelines(self, data):
        if self._open():
            self._f.writelines(data)
        self._fprev.writelines(data)

def capture_stderr(filename=None):
    import sys
    if filename is None:
        filename = sys.argv[0]
        if filename.endswith('.py'):
            filename = filename[:-3]
        filename += '.errors'
    sys.stderr = FiledStderr(sys.stderr, filename)


def run(UdpLookForServer, Display, Sound=None):
    import sys
    server = None
    kw = {}
    mode = Display, Sound, kw
    for arg in sys.argv[1:]:
        if arg == '-udp':
            kw['udp_over_tcp'] = 0
        elif arg == '-no-udp':
            kw['udp_over_tcp'] = 1
        elif ':' in arg:
            Host, Port = sys.argv[1].split(':')
            Port = int(Port)
            server = Host, Port
        else:
            raise ValueError, 'unknown argument %r' % arg
    if server is None:
        import hostchooser
        server = hostchooser.pick(UdpLookForServer * 5)
    import display.pclient
    display.pclient.run(server, mode)
