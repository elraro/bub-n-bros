import struct


MSG_WELCOME = "Welcome to gamesrv.py(3) !\n"
MSG_BROADCAST_PORT= "*"
MSG_DEF_PLAYFIELD = "p"
MSG_DEF_KEY       = "k"
MSG_DEF_ICON      = "r"
MSG_DEF_BITMAP    = "m"
MSG_DEF_SAMPLE    = "w"
MSG_DEF_MUSIC     = "z"
MSG_PLAY_MUSIC    = "Z"
MSG_FADEOUT       = "f"
MSG_PLAYER_JOIN   = "+"
MSG_PLAYER_KILL   = "-"
MSG_PLAYER_ICON   = "i"
MSG_PING          = "g"
MSG_PONG          = "G"
MSG_INLINE_FRAME  = "\\"
#MSG_LOAD_PREFIX   = "F"
MSG_RECORDED      = "\x00"

CMSG_KEY          = "k"
CMSG_ADD_PLAYER   = "+"
CMSG_REMOVE_PLAYER= "-"
CMSG_UDP_PORT     = "<"
CMSG_ENABLE_SOUND = "s"
CMSG_ENABLE_MUSIC = "m"
CMSG_PING         = "g"
CMSG_PONG         = "G"
#CMSG_DEF_FILE     = "F"


def message(tp, *values):
    strtype = type('')
    typecodes = ['']
    for v in values:
        if type(v) is strtype:
            typecodes.append('%ds' % len(v))
        elif 0 <= v < 256:
            typecodes.append('B')
        else:
            typecodes.append('l')
    typecodes = ''.join(typecodes)
    assert len(typecodes) < 256
    return struct.pack(("!B%dsc" % len(typecodes)) + typecodes,
                       len(typecodes), typecodes, tp, *values)

def decodemessage(data):
    if data:
        limit = ord(data[0]) + 1
        if len(data) >= limit:
            typecodes = "!c" + data[1:limit]
            end = limit + struct.calcsize(typecodes)
            if len(data) >= end:
                return struct.unpack(typecodes, data[limit:end]), data[end:]
    return None, data
