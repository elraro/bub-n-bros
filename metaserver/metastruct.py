import sys, os
LOCALDIR = __file__
LOCALDIR = os.path.abspath(os.path.dirname(LOCALDIR))
sys.path.append(os.path.join(LOCALDIR, os.pardir, 'common'))

from msgstruct import *
from socket import error

MMSG_INFO     = 'I'
MMSG_START    = '+'
MMSG_STOP     = '-'
MMSG_LIST     = 'L'
MMSG_ROUTE    = 'R'
MMSG_TRACEBACK= 'T'

RMSG_WAKEUP   = 'w'
RMSG_PING     = 'p'
RMSG_PONG     = 'o'
RMSG_SYNC     = 'y'
RMSG_CONNECT  = 'c'
RMSG_LIST     = 'l'


def encodedict(dict):
    data = []
    for key, value in dict.items():
        data.append(message('#', key, value))
    return ''.join(data)

def encodelist(list):
    return message('[', *list)

def decodedict(buffer):
    result = {}
    while 1:
        msg, buffer = decodemessage(buffer)
        if msg is None or len(msg) < 3 or msg[0] != '#':
            break
        result[msg[1]] = msg[2]
    return result

def decodelist(buffer):
    msg, buffer = decodemessage(buffer)
    assert msg[0] == '['
    return list(msg[1:])


class MessageSocket:
    
    def __init__(self, s):
        self.s = s
        self.buffer = ""

    def receive(self):
        try:
            data = self.s.recv(2048)
        except error:
            data = ''
        if not data:
            self.disconnect()
            return
        self.buffer += data
        while 1:
            msg, self.buffer = decodemessage(self.buffer)
            if msg is None:
                break
            if msg[0] not in self.MESSAGES:
                print >> sys.stderr, 'unknown message %r' % (msg[0],)
            else:
                fn = self.MESSAGES[msg[0]]
                fn(self, *msg[1:])
