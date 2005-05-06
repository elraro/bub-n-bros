import sys, os, time
from socket import *
from metastruct import *

METASERVER = ('codespeak.net', 8055)
METASERVER_URL = 'http://codespeak.net:8050/bub-n-bros.html'
#METASERVER = ('127.0.0.1', 8055)
#METASERVER_URL = 'http://127.0.0.1:8050/bub-n-bros.html'

def connect(failure=[]):
    if len(failure) >= 2:
        return None
    print >> sys.stderr, 'Connecting to the meta-server %s:%d...' % METASERVER
    try:
        s = socket(AF_INET, SOCK_STREAM)
        s.connect(METASERVER)
    except error, e:
        print >> sys.stderr, '*** cannot contact meta-server:', str(e)
        failure.append(e)
        return None
    else:
        print >> sys.stderr, 'connected.'
    return s

sys.setcheckinterval(4096)


def float2str(f):
    # don't trust locale issues and write a string with a '.'
    s = str(long(f*1000000.0))
    return s[:-6] + '.' + s[-6:]

def str2float(s):
    try:
        return float(s)
    except:
        # locale issues may prevent float() from decoding the string
        s = s.strip()
        try:
            i = s.index('.')
        except ValueError:
            try:
                i = s.index(',')
            except ValueError:
                i = len(s)
        frac = s[i+1:]
        return float(s[:i] or '0') + float(frac or '0')/(10**len(frac))


# ____________________________________________________________
# Game Servers

class MetaClientSrv(MessageSocket):
    
    def __init__(self, s, game):
        MessageSocket.__init__(self, s)
        self.game = game
        self.lastwakeup = None
        self.synsockets = {}
        import gamesrv
        gamesrv.addsocket('META', s, self.receive)
        self.closed = 0

    def close(self):
        if not self.closed:
            self.disconnect()
            try:
                self.s.shutdown(2)
            except:
                pass

    def disconnect(self):
        import gamesrv
        gamesrv.removesocket('META', self.s)
        self.closed = 1
        print >> sys.stderr, 'disconnected from the meta-server'

    def send_traceback(self):
        if not self.closed:
            import traceback, cStringIO, sys
            f = cStringIO.StringIO()
            print >> f, sys.version
            print >> f, (sys.platform, sys.executable, sys.argv)
            traceback.print_exc(file = f)
            self.s.sendall(message(MMSG_TRACEBACK, f.getvalue()))

    def msg_wakeup(self, origin, *rest):
        if self.lastwakeup is None or time.time()-self.lastwakeup > 4.0:
            def fastresponses(wakeup):
                sys.setcheckinterval(64)
                time.sleep(12.01)
                if self.lastwakeup == wakeup:
                    sys.setcheckinterval(4096)
                    self.synsockets.clear()
            import thread
            self.lastwakeup = time.time()
            thread.start_new_thread(fastresponses, (self.lastwakeup,))

    def msg_connect(self, origin, port, *rest):
        def connect(origin, port):
            host, _ = origin.split(':')
            addr = host, port
            s = socket(AF_INET, SOCK_STREAM)
            print >> sys.stderr, 'backconnecting to', addr
            try:
                s.connect(addr)
            except error, e:
                print >> sys.stderr, 'backconnecting:', str(e)
            else:
                self.game.newclient(s, addr)
        import thread
        thread.start_new_thread(connect, (origin, port))

    def msg_ping(self, origin, *rest):
        # ping time1  -->  pong time2 time1
        self.s.sendall(message(MMSG_ROUTE, origin,
                               RMSG_PONG, float2str(time.time()), *rest))

    def msg_sync(self, origin, clientport, time3, time2, time1, *rest):
        time4 = time.time()
        s = socket(AF_INET, SOCK_STREAM)
        s.bind(('', INADDR_ANY))
        _, serverport = s.getsockname()
        self.s.sendall(message(MMSG_ROUTE, origin,
                               RMSG_CONNECT, serverport, clientport))
        #print 'times:', time1, time2, time3, time4
        doubleping = (str2float(time3)-str2float(time1)) + (time4-str2float(time2))
        connecttime = time4 + doubleping / 4.0
        def connect(origin, port, connecttime, s):
            host, _ = origin.split(':')
            addr = host, port
            delay = connecttime - time.time()
            #print 'sleep(%r)' % delay
            if 0.0 <= delay <= 10.0:
                time.sleep(delay)
            print >> sys.stderr, 'synconnecting to', addr
            try:
                s.connect(addr)
            except error, e:
                print >> sys.stderr, 'synconnecting:', str(e)
            else:
                self.game.newclient(s, addr)
        import thread
        thread.start_new_thread(connect, (origin, clientport, connecttime, s))

    MESSAGES = {
        RMSG_CONNECT: msg_connect,
        RMSG_WAKEUP:  msg_wakeup,
        RMSG_PING:    msg_ping,
        RMSG_SYNC:    msg_sync,
        }

metaclisrv = None

def meta_register(game):
    global metaclisrv
    import gamesrv
    info = {}
    if game.FnDesc:
        info['desc'] = game.FnDesc or ''
        info['extradesc'] = game.FnExtraDesc() or ''

    s = gamesrv.opentcpsocket()
    hs = gamesrv.openhttpsocket()
    port = int(gamesrv.displaysockport(s))
    info['httpport'] = gamesrv.displaysockport(hs)

    if not metaclisrv or metaclisrv.closed:
        s = connect()
        if not s:
            return
        metaclisrv = MetaClientSrv(s, game)
    metaclisrv.s.sendall(message(MMSG_INFO, encodedict(info)) +
                         message(MMSG_START, port))

def meta_unregister(game):
    global metaclisrv
    if metaclisrv:
        metaclisrv.close()
        metaclisrv = None


# ____________________________________________________________
# Game Clients

class Event:
    def __init__(self):
        import thread
        self.lock = thread.allocate_lock()
        self.lock.acquire()
    def signal(self):
        try:
            self.lock.release()
        except:
            pass
    def wait1(self):
        self.lock.acquire()


class MetaClientCli:
    
    def __init__(self, serverkey, backconnectport):
        self.resultsocket = None
        self.serverkey = serverkey
        self.backconnectport = backconnectport
        self.threads = {}

    def run(self):
        import thread
        print >> sys.stderr, 'Trying to connect to', self.serverkey
        self.ev = Event()
        thread.start_new_thread(self.bipbip, ())
        self.startthread(self.try_direct_connect)
        self.startthread(self.try_indirect_connect, 0.75)
        while self.resultsocket is None:
            self.threadsleft()
            self.ev.wait1()
        return self.resultsocket

    def done(self):
        sys.setcheckinterval(4096)

    def bipbip(self):
        while self.resultsocket is None:
            time.sleep(0.31416)
            self.ev.signal()

    def startthread(self, fn, sleep=0.0, args=()):
        import thread
        def bootstrap(fn, atom, sleep, args):
            try:
                time.sleep(sleep)
                if self.resultsocket is None:
                    fn(*args)
            finally:
                del self.threads[atom]
                self.ev.signal()
        atom = object()
        self.threads[atom] = time.time()
        thread.start_new_thread(bootstrap, (fn, atom, sleep, args))

    def threadsleft(self):
        now = time.time()
        TIMEOUT = 10
        for starttime in self.threads.values():
            if now < starttime + TIMEOUT:
                break
        else:
            if self.threads:
                print >> sys.stderr, '*** time out, giving up.'
            else:
                print >> sys.stderr, '*** failed to connect.'
            sys.exit(1)

    def try_direct_connect(self):
        host, port = self.serverkey.split(':')
        port = int(port)
        s = socket(AF_INET, SOCK_STREAM)
        try:
            s.connect((host, port))
        except error, e:
            print >> sys.stderr, 'direct connexion failed:', str(e)
        else:
            print >> sys.stderr, 'direct connexion accepted.'
            self.resultsocket = s

    def try_indirect_connect(self):
        import thread, time
        self.s = connect()
        if not self.s: return
        self.buffer = ""
        self.sendlock = thread.allocate_lock()
        self.routemsg(RMSG_WAKEUP)
        self.startthread(self.try_backconnect)
        self.socketcache = {}
        tries = [0.6, 0.81, 1.2, 1.69, 2.6, 3.6, 4.9, 6.23]
        for delay in tries:
            self.startthread(self.send_ping, delay)
        while self.resultsocket is None:
            msg = self.inputmsg()
            now = time.time()
            if self.resultsocket is not None:
                break
            if msg[0] == RMSG_CONNECT:
                # connect serverport clientport
                self.startthread(self.try_synconnect, args=msg[1:])
            if msg[0] == RMSG_PONG:
                # pong time2 time1  -->  sync port time3 time2 time1
                if len(self.socketcache) < len(tries):
                    s = socket(AF_INET, SOCK_STREAM)
                    s.bind(('', INADDR_ANY))
                    _, port = s.getsockname()
                    self.socketcache[port] = s
                    self.routemsg(RMSG_SYNC, port, float2str(now), *msg[2:])

    def routemsg(self, *rest):
        data = message(MMSG_ROUTE, self.serverkey, *rest)
        self.sendlock.acquire()
        try:
            self.s.sendall(data)
        finally:
            self.sendlock.release()

    def inputmsg(self):
        while 1:
            msg, self.buffer = decodemessage(self.buffer)
            if msg is not None:
                break
            data = self.s.recv(2048)
            if not data:
                print >> sys.stderr, 'disconnected from the meta-server'
                sys.exit()
            self.buffer += data
        return msg

    def try_backconnect(self):
        s1 = socket(AF_INET, SOCK_STREAM)
        s1.bind(('', self.backconnectport or INADDR_ANY))
        s1.listen(1)
        _, port = s1.getsockname()
        self.routemsg(RMSG_CONNECT, port)
        print >> sys.stderr, 'listening for backward connection'
        s, addr = s1.accept()
        print >> sys.stderr, 'accepted backward connection from', addr
        self.resultsocket = s

    def send_ping(self):
        sys.stderr.write('. ')
        self.routemsg(RMSG_PING, float2str(time.time()))

    def try_synconnect(self, origin, remoteport, localport, *rest):
        sys.stderr.write('+ ')
        s = self.socketcache[localport]
        remotehost, _ = origin.split(':')
        remoteaddr = remotehost, remoteport
        s.connect(remoteaddr)
        print >> sys.stderr, ('simultaneous SYN connect succeeded with %s:%d' %
                              remoteaddr)
        self.resultsocket = s


def meta_connect(serverkey, backconnectport=None):
    c = MetaClientCli(serverkey, backconnectport)
    s = c.run()
    c.done()
    return s

def print_server_list():
    s = connect()
    if s is not None:
        s.sendall(message(MMSG_LIST))
        buffer = ""
        while decodemessage(buffer)[0] is None:
            buffer += s.recv(8192)
        s.close()
        msg = decodemessage(buffer)[0]
        assert msg[0] == RMSG_LIST
        entries = decodedict(msg[1])
        if not entries:
            print >> sys.stderr, 'No registered server.'
        else:
            print
            print ' %-25s | %-30s | %s' % (
                'server', 'game', 'players')
            print '-'*27+'+'+'-'*32+'+'+'-'*11
            for key, value in entries.items():
                value = decodedict(value)
                print ' %-25s | %-30s | %s' % (
                    key, value.get('desc', '<no description>'),
                    value.get('extradesc', ''))
            print

if __name__ == '__main__':
    print_server_list()
