from socket import *
import time, select, sys
from errno import ETIMEDOUT

UDP_PORT     = 8056
PING_MESSAGE = "pclient-game-ping"
PONG_MESSAGE = "server-game-pong"

BROADCAST_PORT_RANGE = xrange(18000, 19000)
BROADCAST_MESSAGE    = "game!"   # less than 6 bytes
BROADCAST_DELAY      = 0.6180
BROADCAST_DELAY_INCR = 2.7183


def serverside_ping():
    s = socket(AF_INET, SOCK_DGRAM)
    try:
        s.bind(('', UDP_PORT))
        s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        return (s, UDP_PORT)
    except error, e:
        s = socket(AF_INET, SOCK_DGRAM)
        s.bind(('', INADDR_ANY))
        HOST, PORT = s.getsockname()
        return s, PORT

def answer_ping(s, descr, addr):
    data, source = s.recvfrom(100)
    if data == PING_MESSAGE:
        print "ping by", source
        s.sendto('%s:%s:%s:%d' % ((PONG_MESSAGE, descr,)+addr), source)
    else:
        print >> sys.stderr, \
              "unexpected data on UDP port %d by" % UDP_PORT, source


def pick(hostlist, delay=1):
    s = socket(AF_INET, SOCK_DGRAM)
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    for host in hostlist:
        print "* Looking for a server on %s... " % host
        try:
            s.sendto(PING_MESSAGE, (host, UDP_PORT))
        except error, e:
            print >> sys.stderr, str(e)
            continue
        while 1:
            iwtd, owtd, ewtd = select.select([s], [], [], delay)
            if not iwtd:
                break
            try:
                data, answer_from = s.recvfrom(200)
            except error, e:
                if e.args[0] != ETIMEDOUT:
                    print >> sys.stderr, str(e)
                    continue
                break
            data = data.split(':')
            if len(data) >= 4 and data[0] == PONG_MESSAGE:
                hostname = data[2] or answer_from[0]
                try:
                    port = int(data[3])
                except ValueError:
                    pass
                else:
                    result = (hostname, port)
                    print "* Picking %r at" % data[1], result
                    return result
            print >> sys.stderr, "got an unexpected answer from", answer_from
    print >> sys.stderr, "no server found."
    raise SystemExit

def find_servers(hostlist=[('255.255.255.255', None)], tries=2, delay=0.5):
    servers = {}
    s = socket(AF_INET, SOCK_DGRAM)
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    for trynum in range(tries):
        for host, udpport in hostlist:
            try:
                s.sendto(PING_MESSAGE, (host, udpport or UDP_PORT))
            except error, e:
                print >> sys.stderr, str(e)
                continue
        while 1:
            iwtd, owtd, ewtd = select.select([s], [], [], delay)
            if not iwtd:
                break
            try:
                data, answer_from = s.recvfrom(200)
            except error, e:
                if e.args[0] != ETIMEDOUT:
                    print >> sys.stderr, str(e)
                    continue
                break
            data = data.split(':')
            if len(data) >= 4 and data[0] == PONG_MESSAGE:
                hostname = data[2] or answer_from[0]
                try:
                    port = int(data[3])
                except ValueError:
                    pass
                else:
                    result = (hostname, port)
                    servers[result] = data[1]
            else:
                print >> sys.stderr, "got an unexpected answer from", answer_from
    return servers
