#! /usr/bin/env python

#
#  This script is used to start the server.
#  Use with '--help' for more information.
#
#  It is actually just a wrapper around bubbob/bb.py
#  with some more magic to launch the web browser.
#

import sys, os

if __name__ == '__main__':
    LOCALDIR = sys.argv[0]
else:
    LOCALDIR = __file__
LOCALDIR = os.path.abspath(os.path.dirname(LOCALDIR))
sys.path.append(LOCALDIR)

def look_for_local_server(tries, verbose):
    # Look for a running local web server
    from common.hostchooser import find_servers
    servers = find_servers([('127.0.0.1', None)], tries=tries,
                           delay=0.5, verbose=verbose, port_needed=0)
    httpport = 'off'
    if servers:
        info, ping = servers.values()[0]
        infolst = info.split(':')
        if len(infolst) >= 3:
            httpport = infolst[2]
    try:
        httpport = int(httpport)
    except ValueError:
        return ''
    else:
        return 'http://127.0.0.1:%d/controlcenter.html' % httpport

def start_local_server():
    url = ''
    MAINSCRIPT = os.path.abspath(os.path.join(LOCALDIR, 'bubbob', 'bb.py'))
    args = [sys.executable, MAINSCRIPT]
    try:
        readpipe, writepipe = os.pipe()
    except:
        readpipe, writepipe = None
    else:
        args.append('--pipeurlto=%d,%d' % (readpipe, writepipe))
    os.spawnv(os.P_NOWAITO, args[0], args)
    if readpipe is not None:
        os.close(writepipe)
        while 1:
            try:
                t = os.read(readpipe, 128)
                if not t:
                    break
            except OSError:
                return ''
            url += t
        os.close(readpipe)
    return url


# main
url = look_for_local_server(tries=1, verbose=0)
if not url:
    url = start_local_server()
    if not url:
        # wait for up to 5 seconds for the server to start
        url = look_for_local_server(tries=10, verbose=1)
        if not url:
            print >> sys.stderr, 'The local server is not starting, giving up.'
            sys.exit(1)

try:
    import webbrowser
    browser = webbrowser.get()
    name = getattr(browser, 'name', browser.__class__.__name__)
    print "Trying to open '%s' with '%s'..." % (url, name)
    browser.open(url)
except:
    exc, val, tb = sys.exc_info()
    print '-'*60
    print >> sys.stderr, "Failed to launch the web browser:"
    print >> sys.stderr, "  %s: %s" % (exc.__name__, val)
    print
    print "Sorry, I guess you have to go to the following URL manually:"
else:
    print "Done running '%s'." % name
    print
    print '-'*60
    print "If the browser fails to open the page automatically,"
    print "you will have to manually go to the following URL:"
print ' ', url
print '-'*60
print "The server is running in the background. Please remember to use"
print "the 'Stop this program' link to cleanly stop it."
