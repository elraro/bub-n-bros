import sys, os, time
from socket import *
from metastruct import *

METASERVER = ('codespeak.net', 8055)
METASERVER_URL = 'http://codespeak.net:8050/bub-n-bros.html'
#METASERVER = ('127.0.0.1', 8055)
#METASERVER_URL = 'http://127.0.0.1:8050/bub-n-bros.html'

def connect():
    print 'Connecting to the meta-server %s:%d...' % METASERVER
    try:
        s = socket(AF_INET, SOCK_STREAM)
        s.connect(METASERVER)
    except error, e:
        print >> sys.stderr, '*** cannot contact meta-server:', str(e)
        return None
    else:
        print 'connected.'
    return s

sys.setcheckinterval(4096)


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
        print 'disconnected from the meta-server'

    def send_traceback(self):
        if not self.closed:
            import traceback, cStringIO
            f = cStringIO.StringIO()
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
            print 'backconnecting to', addr
            try:
                s.connect(addr)
            except error, e:
                print 'backconnecting:', str(e)
            else:
                self.game.newclient(s, addr)
        import thread
        thread.start_new_thread(connect, (origin, port))

    def msg_ping(self, origin, *rest):
        # ping time1  -->  pong time2 time1
        self.s.sendall(message(MMSG_ROUTE, origin,
                               RMSG_PONG, str(time.time()), *rest))

    def msg_sync(self, origin, clientport, time3, time2, time1, *rest):
        time4 = time.time()
        s = socket(AF_INET, SOCK_STREAM)
        s.bind(('', INADDR_ANY))
        _, serverport = s.getsockname()
        self.s.sendall(message(MMSG_ROUTE, origin,
                               RMSG_CONNECT, serverport, clientport))
        #print 'times:', time1, time2, time3, time4
        doubleping = (float(time3)-float(time1)) + (time4-float(time2))
        connecttime = time4 + doubleping / 4.0
        def connect(origin, port, connecttime, s):
            host, _ = origin.split(':')
            addr = host, port
            delay = connecttime - time.time()
            #print 'sleep(%r)' % delay
            if 0.0 <= delay <= 10.0:
                time.sleep(delay)
            print 'synconnecting to', addr
            try:
                s.connect(addr)
            except error, e:
                print 'synconnecting:', str(e)
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
        print 'Trying to connect to', self.serverkey
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
                print '*** time out, giving up.'
            else:
                print '*** failed to connect.'
            sys.exit(1)

    def try_direct_connect(self):
        host, port = self.serverkey.split(':')
        port = int(port)
        s = socket(AF_INET, SOCK_STREAM)
        try:
            s.connect((host, port))
        except error, e:
            print 'direct connexion failed:', str(e)
        else:
            print 'direct connexion accepted.'
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
                    self.routemsg(RMSG_SYNC, port, str(now), *msg[2:])

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
                print 'disconnected from the meta-server'
                sys.exit()
            self.buffer += data
        return msg

    def try_backconnect(self):
        s1 = socket(AF_INET, SOCK_STREAM)
        s1.bind(('', self.backconnectport or INADDR_ANY))
        s1.listen(1)
        _, port = s1.getsockname()
        self.routemsg(RMSG_CONNECT, port)
        print 'listening for backward connection'
        s, addr = s1.accept()
        print 'accepted backward connection from', addr
        self.resultsocket = s

    def send_ping(self):
        sys.stderr.write('. ')
        self.routemsg(RMSG_PING, str(time.time()))

    def try_synconnect(self, origin, remoteport, localport, *rest):
        sys.stderr.write('+ ')
        s = self.socketcache[localport]
        remotehost, _ = origin.split(':')
        remoteaddr = remotehost, remoteport
        s.connect(remoteaddr)
        print 'simultaneous SYN connect succeeded with %s:%d' % remoteaddr
        self.resultsocket = s


def meta_connect(serverkey, backconnectport=None):
    c = MetaClientCli(serverkey, backconnectport)
    s = c.run()
    c.done()
    return s