#! /usr/bin/env python

from socket import *


# Display engine. One of 'pygame', 'X' or 'shm'.
Display = 'shm'


# machine addresses to look for a game server.
# Each name may also be '127.0.0.1' for the local machine
# or '255.255.255.255' for broadcast.
# Servers listen for queries on UDP port 8056 by default.

UdpLookForServer = [
    '127.0.0.1',
    '255.255.255.255',
    'magma.unil.ch',
    ]


# End of configuration

import common
common.run(UdpLookForServer, Display)
