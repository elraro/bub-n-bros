import os, sys, random
from cStringIO import StringIO
import socket, time

try:
    FILE = __file__
except NameError:
    FILE = sys.argv[0]
LOCALDIR = os.path.abspath(os.path.dirname(FILE))
METASERVER = "http://bub-n-bros.sourceforge.net/cgi-bin/bb12.py"
#METASERVER = "http://127.0.0.1/cgi-bin/bb12.py"

sys.path.append(os.path.abspath(os.path.join(LOCALDIR, os.pardir, 'common')))
sys.path.append(os.path.abspath(os.path.join(LOCALDIR, os.pardir)))
import gamesrv, httpserver, hostchooser
from httpserver import HTTPRequestError


class Options:
    def __init__(self, dict={}):
        self.update(dict)
    def dict(self):
        return self.__dict__.copy()
    def update(self, dict):
        self.__dict__.update(dict)
    def copy(self):
        return Options(self.__dict__)
    def clear(self):
        self.__dict__.clear()
    def __getattr__(self, attr):
        if not attr.startswith('_'):
            return None
        else:
            raise AttributeError, attr


class PageServer:
    CONFIGFILE = 'config.txt'

    def __init__(self, Game):
        self.Game = Game
        self.seed = hex(random.randrange(0x1000, 0x10000))
        self.unique_actions = {}
        self.localhost = socket.gethostname()
        self.filename = os.path.join(LOCALDIR, self.CONFIGFILE)
        data = self.loadoptionfile()
        self.globaloptions = Options(data.get('*', {}))
        self.localoptions  = Options(data.get(self.localhost, {}))
        self.inetserverlist = None
        self.inetservers = {}
        self.has_been_published = 0

    def registerpages(self):
        prefix = '%s/' % self.seed
        httpserver.register('controlcenter.html',  self.controlcenterloader)
        httpserver.register(prefix,                self.indexloader)
        httpserver.register(prefix+'index.html',   self.indexloader)
        httpserver.register(prefix+'list.html',    self.listloader)
        httpserver.register(prefix+'new.html',     self.newloader)
        httpserver.register(prefix+'run.html',     self.runloader)
        httpserver.register(prefix+'stop.html',    self.stoploader)
        httpserver.register(prefix+'join.html',    self.joinloader)
        httpserver.register(prefix+'register.html',self.registerloader)
        httpserver.register(prefix+'options.html', self.optionsloader)
        httpserver.register(prefix+'name.html',    self.nameloader)
        for fn in os.listdir(os.path.join(LOCALDIR, 'data')):
            path = prefix + fn
            if not httpserver.is_registered(path):
                httpserver.register(path, httpserver.fileloader(
                    os.path.join(LOCALDIR, 'data', fn)))

    def opensocket(self):
        hs = gamesrv.openhttpsocket()
        if hs is None:
            return 0
        self.httpport = port = gamesrv.displaysockport(hs)
        self.indexurl = 'http://127.0.0.1:%d/%s/' % (port, self.seed)
        print self.Game.FnDesc, 'server is ready at', self.indexurl
        return 1

    def getlocalservers(self):
        if self.localservers is None:
            self.searchlocalservers()
        return self.localservers

    def searchlocalservers(self):
        servers = hostchooser.find_servers().items()
        servers = filter(self.filterserver, servers)
        servers.sort()
        self.localservers = servers

    def parse_inetserv(self, s):
        try:
            host, port, udpport, httpport = s.split(':')
            return host, int(port), int(udpport)
        except (ValueError, IndexError):
            return None, None, None

    def getinetservers(self):
        if self.inetserverlist is None:
            return None
        result = []
        for s in self.inetserverlist:
            host, port, udpport = self.parse_inetserv(s)
            addr = host, port
            if addr in self.inetservers:
                result.append((addr, self.inetservers[addr]))
        return result

    def setinetserverlist(self, lst):
        self.inetserverlist = lst

    def checkinetserverlist(self):
        ulist = []
        for s in self.inetserverlist:
            host, port, udpport = self.parse_inetserv(s)
            if host is not None:
                ulist.append((host, udpport))
        srvs = hostchooser.find_servers(ulist, delay=0.8)
        self.inetservers = {}
        for srv in srvs.items():
            if not self.filterserver(srv):
                continue
            (host, port), info = srv
            try:
                host = socket.gethostbyaddr(host)[0]
            except socket.error:
                pass
            self.inetservers[host, port] = info
        #print 'hostchooser:', self.inetserverlist, '->', self.inetservers

    def filterserver(self, ((host, port), info)):
        for c in host+str(port):
            if c not in "-.0123456789:@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_abcdefghijklmnopqrstuvwxyz":
                return 0
        return 1

    def statusservers(self):
        result = [], []
        for s in self.inetserverlist:
            host, port, udpport = self.parse_inetserv(s)
            addr = host, port
            found = addr in self.inetservers
            result[found].append(s)
        return result

    def loadoptionfile(self):
        try:
            f = open(self.filename, 'r')
            data = f.read().strip()
            f.close()
        except IOError:
            data = None
        return eval(data or '{}', {}, {})

    def saveoptions(self):
        data = self.loadoptionfile()
        data['*'] = self.globaloptions.dict()
        data[self.localhost] = self.localoptions.dict()
        try:
            f = open(self.filename, 'w')
            print >> f, `data`
            f.close()
        except IOError, e:
            print >> sys.stderr, "! Cannot save config file: " + str(e)

    def startgame(self):
        options = self.globaloptions
        kwds = {}
        if options.beginboard is not None:
            kwds['beginboard'] = int(options.beginboard)
        if options.stepboard is not None:
            kwds['stepboard'] = int(options.stepboard)
        if options.limit == 'y':
            kwds['limitlives'] = int(options.lives)
        if options.extralife is not None:
            kwds['extralife'] = int(options.extralife)
        if options.autoreset is not None:
            kwds['autoreset'] = options.autoreset.startswith('y')
        self.Game(options.file, **kwds)

    ### loaders ###

    def mainpage(self, headers, metaquery=None, juststarted=0):
        servers = self.getlocalservers()
        metaserver = METASERVER
        running = my_server()
        myhost = my_host(headers)
        count = len(gamesrv.clients)
        if running:
            metapublish = my_server_meta_address()
            fndesc = quote_plus(gamesrv.game.FnDesc)
        else:
            metapublish = None
        return httpserver.load(os.path.join(LOCALDIR, 'data', 'index.html'),
                               'text/html', locals=locals())

    def indexloader(self, headers, **options):
        self.searchlocalservers()
        return self.mainpage(headers)

    def controlcenterloader(self, headers, **options):
        host = headers['remote host']
        if host != '127.0.0.1':
            raise HTTPRequestError, "Access denied"
        return None, self.indexurl

    def listloader(self, headers, s=[], **options):
        self.setinetserverlist(s)
        self.checkinetserverlist()
        query = []
        missing, found = self.statusservers()
        for s in missing:
            query.append('d=' + s)
        for s in found:
            query.append('a=' + s)
        return self.mainpage(headers, query)

    def newloader(self, headers, **options):
        locals = {
            'levels': self.Game.FnListBoards(),
            'options': self.globaloptions,
            'running': gamesrv.game is not None,
            }
        return httpserver.load(os.path.join(LOCALDIR, 'data', 'new.html'),
                               'text/html', locals=locals)

    def runloader(self, headers, id, **options):
        id, = id
        juststarted = id not in self.unique_actions
        if juststarted:
            self.globaloptions.metapublish = 'n'
            self.globaloptions.autoreset = 'n'
            for key, value in options.items():
                if len(value) == 1:
                    setattr(self.globaloptions, key, value[0])
            self.saveoptions()
            self.startgame()
            self.unique_actions[id] = 1
        self.searchlocalservers()
        return self.mainpage(headers, juststarted=juststarted)

    def stoploader(self, headers, really=[], **options):
        count = len(gamesrv.clients)
        if count == 0 or really:
            locals = {
                'self': self,
                'metaserver': METASERVER,
                'metapublish': gamesrv.game and my_server_meta_address(),
                'localdir': LOCALDIR,
                }
            gamesrv.closeeverything()
            return httpserver.load(os.path.join(LOCALDIR, 'data', 'stop.html'),
                                   'text/html', locals=locals)
        else:
            locals = {
                'count': count,
                }
            return httpserver.load(os.path.join(LOCALDIR, 'data', 'confirm.html'),
                                   'text/html', locals=locals)

    def registerloader(self, headers, a=[], d=[], **options):
        if a:  # the lists 'a' and 'd' contain dummies !!
            self.globaloptions.metapublish = 'y'
            self.has_been_published = 1
            kwd = 'a'
        else:
            self.globaloptions.metapublish = 'n'
            kwd = 'd'
        url = "%s?cmd=register&%s=%s" % (METASERVER,
                                         kwd, my_server_meta_address())
        if a and gamesrv.game:
            url += '&desc=' + quote_plus(gamesrv.game.FnDesc)
        return None, url

    def joinloader(self, headers, host=[], port=[], httpport=[], **options):
        args = self.buildclientoptions()
        assert len(host) == len(port) == 1
        if args is None:
            # redirect to the Java applet
            try:
                httpport = int(httpport[0])
            except (ValueError, IndexError):
                raise HTTPRequestError, "This server is not running HTTP."
            return None, 'http://%s:%s/' % (host[0], httpport)
        
        address = '%s:%s' % (host[0], port[0])
        nbclients = len(gamesrv.clients)
        script = os.path.join(LOCALDIR, os.pardir, 'display', 'main.py')
        args = [script] + args + [address]
        launch(args)
        if my_server_address() == address:
            endtime = time.time() + 3.0
            while gamesrv.recursiveloop(endtime, []):
                if len(gamesrv.clients) > nbclients:
                    break
        return self.mainpage(headers)

    def optionsloader(self, headers, reset=[], **options):
        if reset:
            self.localoptions.clear()
            self.globaloptions.clear()
            self.saveoptions()
        elif options:
            for key, value in options.items():
                setattr(self.localoptions, key, value[0])
            self.saveoptions()
        locals = {
            'graphicmodes': self.graphicmodeslist(),
            'soundmodes'  : self.soundmodeslist(),
            'currentmodes': self.localmodes(),
            'options'     : self.localoptions,
            }
        locals['java'] = locals['graphicmodes'][0] in locals['currentmodes']
        return httpserver.load(os.path.join(LOCALDIR, 'data', 'options.html'),
                               'text/html', locals=locals)

    def nameloader(self, headers, **options):
        if options:
            anyname = None
            for id in range(7):
                keyid = 'player%d' % id
                value = options.get(keyid, [''])[0]
                anyname = anyname or value
                setattr(self.localoptions, keyid, value)
            if 'c' in options:
                for id in range(7):
                    keyid = 'player%d' % id
                    try:
                        delattr(self.localoptions, keyid)
                    except AttributeError:
                        pass
            if 'f' in options:
                for id in range(7):
                    keyid = 'player%d' % id
                    if not getattr(self.localoptions, keyid):
                        setattr(self.localoptions, keyid,
                                anyname or ['Bub', 'Bob', 'Boob', 'Beb',
                                            'Biob', 'Bab', 'Bib'][id])
                    else:
                        anyname = getattr(self.localoptions, keyid)
            self.saveoptions()
            if 's' in options:
                return self.mainpage(headers)
        locals = {
            'options': self.localoptions,
            }
        return httpserver.load(os.path.join(LOCALDIR, 'data', 'name.html'),
                               'text/html', locals=locals)

    def graphicmodeslist(self):
        try:
            return self.GraphicModesList
        except AttributeError:
            import display.modes
            self.GraphicModesList = display.modes.graphicmodeslist()
            javamode = display.modes.GraphicMode(
                'java', 'Java Applet (for Java browsers)', [])
            javamode.low_priority = 1
            javamode.getmodule = lambda : None
            self.GraphicModesList.insert(0, javamode)
            return self.GraphicModesList

    def soundmodeslist(self):
        try:
            return self.SoundModesList
        except AttributeError:
            import display.modes
            self.SoundModesList = display.modes.soundmodeslist()
            return self.SoundModesList

    def localmodes(self):
        import display.modes
        currentmodes = []
        options = self.localoptions
        for name, lst in [(options.dpy_, self.graphicmodeslist()),
                          (options.snd_, self.soundmodeslist())]:
            try:
                mode = display.modes.findmode(name, lst)
            except KeyError:
                try:
                    mode = display.modes.findmode(None, lst)
                except KeyError, e:
                    print >> sys.stderr, str(e)  # no mode!
                    mode = None
            currentmodes.append(mode)
        return currentmodes

    def buildclientoptions(self):
        dpy, snd = self.localmodes()
        if dpy.getmodule() is None:
            return None  # redirect to the Java applet
        if dpy is None or snd is None:
            raise HTTPRequestError, "No installed graphics or sounds drivers. See the settings page."
        options = self.localoptions
        result = ['--cfg='+self.filename]
        if options.datachannel == 'tcp': result.append('--tcp')
        if options.datachannel == 'udp': result.append('--udp')
        if options.music       == 'no':  result.append('--music=no')
        for optname, mode in [('--display', dpy),
                              ('--sound',   snd)]:
            result.append(optname + '=' + mode.name)
            uid = mode.unique_id() + '_'
            for key, value in options.dict().items():
                if key.startswith(uid):
                    result.append('--%s=%s' % (key[len(uid):], value))
        return result

def my_host(headers):
    return headers.get('host') or httpserver.my_host()

def my_server():
    if gamesrv.game:
        s = gamesrv.opentcpsocket()
        return ((socket.gethostname(), gamesrv.displaysockport(s)),
                gamesrv.game.FnDesc)
    else:
        return None

def my_server_address():
    running = my_server()
    if running:
        (host, port), info = running
        return '%s:%d' % (host, port)
    else:
        return None

def my_server_meta_address():
    s = gamesrv.opentcpsocket()
    ps = gamesrv.openpingsocket()
    hs = gamesrv.openhttpsocket()
    fullname = socket.gethostname()
    try:
        fullname = socket.gethostbyaddr(fullname)[0]
    except socket.error:
        pass
    return '%s:%s:%s:%s' % (fullname,
                            gamesrv.displaysockport(s),
                            gamesrv.displaysockport(ps),
                            gamesrv.displaysockport(hs))

def meta_register():
    # Note: this tries to open a direct HTTP connection to the meta-server
    #       which may not work if the proxy is not configured in $http_proxy
    try:
        import urllib
    except ImportError:
        print >> sys.stderr, "cannot register with the meta-server: Python's urllib missing"
        return
    print "registering with the meta-server...",
    sys.stdout.flush()
    addr = my_server_meta_address()
    try:
        f = urllib.urlopen('%s?a=%s&desc=%s' % (
            METASERVER, addr, quote_plus(gamesrv.game.FnDesc)))
        f.close()
    except Exception, e:
        print
        print >> sys.stderr, "cannot contact the meta-server (check $http_proxy):"
        print >> sys.stderr, "%s: %s" % (e.__class__.__name__, e)
    else:
        print "ok"
        unregister_at_exit(addr)

def meta_unregister(addr):
    import urllib
    print "unregistering from the meta-server...",
    sys.stdout.flush()
    try:
        f = urllib.urlopen(METASERVER + '?d=' + addr)
        f.close()
    except Exception, e:
        print "failed"
    else:
        print "ok"

def unregister_at_exit(addr, firsttime=[1]):
    if firsttime:
        import atexit
        atexit.register(meta_unregister, addr)
        del firsttime[:]

QuoteTranslation = {}
for c in ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
          'abcdefghijklmnopqrstuvwxyz'
          '0123456789' '_.-'):
    QuoteTranslation[c] = c
del c
QuoteTranslation[' '] = '+'

def quote_plus(s):
    """Quote the query fragment of a URL; replacing ' ' with '+'"""
    getter = QuoteTranslation.get
    return ''.join([getter(c, '%%%02X' % ord(c)) for c in s])


def main(Game, pipe_url_to=None, quiet=0):
    gamesrv.openpingsocket(0)  # try to reserve the standard UDP port
    srv = PageServer(Game)
    srv.registerpages()
    if not srv.opensocket():
        print >> sys.stderr, "server aborted."
        sys.exit(1)
    if quiet:
        Game.Quiet = 1
        import stdlog
        f = stdlog.LogFile()
        if f:
            print "Logging to", f.filename
            sys.stdout = sys.stderr = f
    if pipe_url_to is not None:
        url = srv.indexurl
        while url:
            url = url[os.write(pipe_url_to, url):]
        os.close(pipe_url_to)
    #if webbrowser:
    #    srv.launchbrowser()


def launch(args):
    # platform-specific hacks
    if sys.platform == 'darwin':   # must start as a UI process
        import tempfile
        cmdname = tempfile.mktemp(prefix='BubBob_', suffix='.command')
        f = open(cmdname, 'w')
        print >> f, "#!", sys.executable
        print >> f, "import os, sys"
        print >> f, "try: os.unlink(%r)" % cmdname
        print >> f, "except OSError: pass"
        print >> f, "sys.argv[:] = %r" % (args,)
        print >> f, "__file__ = %r" % args[0]
        print >> f, "execfile(%r)" % args[0]
        f.close()
        os.chmod(cmdname, 0700)
        args = ['/usr/bin/open', cmdname]
    else:
        args.insert(0, sys.executable)
    print '*', ' '.join(args)
    # try to close the open fds first
    if hasattr(os, 'fork'):
        try:
            from resource import getrlimit, RLIMIT_NOFILE, error
        except ImportError:
            pass
        else:
            try:
                soft, hard = getrlimit(RLIMIT_NOFILE)
            except error:
                pass
            else:
                if os.fork():
                    return # in parent -- done, continue
                # in child
                for fd in range(3, hard):
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                os.execv(args[0], args)
                # this point should never be reached
    # fall-back
    os.spawnv(os.P_NOWAITO, args[0], args)
