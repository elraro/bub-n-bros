import os, sys

if __name__ == '__main__':
    LOCALDIR = sys.argv[0]
else:
    LOCALDIR = __file__
LOCALDIR = os.path.abspath(os.path.dirname(LOCALDIR))

sys.path.append(os.path.abspath(LOCALDIR))
sys.path.append(os.path.abspath(os.path.join(LOCALDIR, os.pardir)))
import common
import pclient
import modes


UdpLookForServer = [
    '127.0.0.1',
    '255.255.255.255',
    ]

def parse_cmdline(argv):
    # parse command-line
    def usage():
        print >> sys.stderr, 'usage:'
        print >> sys.stderr, '  python Client.py [-d#] [-s#] [extra options] [host[:port]]'
        print >> sys.stderr
        print >> sys.stderr, 'options:'
        print >> sys.stderr, '  host              search for a game on the given machine'
        print >> sys.stderr, '  host:port         connect to the given game server'
        print >> sys.stderr, '                      (default search for any local server)'
        print >> sys.stderr, '  -d#  --display=#  graphic driver (see below)'
        print >> sys.stderr, '  -s#  --sound=#    sound driver (see below)'
        print >> sys.stderr, '       --music=no   disable background music'
        print >> sys.stderr, '  -h   --help       display this text'
        print >> sys.stderr, '  -t   --tcp        for slow or proxy connections'
        print >> sys.stderr, '  -u   --udp        for fast direct connections'
        print >> sys.stderr, '                      (default is to autodetect tcp or udp)'
        print >> sys.stderr
        print >> sys.stderr, 'graphic drivers:'
        for info in modes.graphicmodeslist():
            info.printline(sys.stderr)
        print >> sys.stderr
        print >> sys.stderr, 'sound drivers:'
        for info in modes.soundmodeslist():
            info.printline(sys.stderr)
        print >> sys.stderr
        sys.exit(2)

    shortopts = 'd:s:htu'
    longopts = ['display=', 'sound=', 'music=', 'help', 'tcp', 'udp', 'cfg=']
    for info in modes.graphicmodeslist() + modes.soundmodeslist():
        short, long = info.getformaloptions()
        shortopts += short
        longopts += long
    try:
        from getopt import gnu_getopt as getopt
    except ImportError:
        from getopt import getopt
    from getopt import error
    try:
        opts, args = getopt(argv, shortopts, longopts)
    except error, e:
        print >> sys.stderr, 'Client.py: %s' % str(e)
        print >> sys.stderr
        usage()

    driver = sound = None
    extraopts = {}
    for key, value in opts:
        if key in ('-d', '--display'):
            driver = value
        elif key in ('-s', '--sound'):
            sound = value
        elif key in ('-t', '--tcp'):
            extraopts['udp_over_tcp'] = 1
        elif key in ('-u', '--udp'):
            extraopts['udp_over_tcp'] = 0
        elif key == '--cfg':
            extraopts['cfgfile'] = value
        elif key in ('-h', '--help'):
            usage()
        else:
            extraopts[key] = value
    mode = driver, sound, extraopts

    if args:
        if len(args) > 1:
            usage()
        hosts = args[0].split(':')
        if len(hosts) == 1:
            host, = hosts
            from common import hostchooser
            server = hostchooser.pick([host] * 5)
        elif len(hosts) == 2:
            host, port = hosts
            try:
                port = int(port)
            except ValueError:
                usage()
            server = host, port
        else:
            usage()
    else:
        from common import hostchooser
        server = hostchooser.pick(UdpLookForServer * 3)
    return server, mode

def main():
    server, mode = parse_cmdline(sys.argv[1:])
    pclient.run(server, mode)

if __name__ == '__main__':
    main()
