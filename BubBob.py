#! /usr/bin/env python

#
#  This script is used to start the server.
#  For command-line usage please run
#
#    python bubbob/bb.py --help
#

import sys, os, socket, tempfile

if __name__ == '__main__':
    LOCALDIR = sys.argv[0]
else:
    LOCALDIR = __file__
LOCALDIR = os.path.abspath(os.path.dirname(LOCALDIR))
sys.path.append(LOCALDIR)
sys.argv[0] = os.path.abspath(sys.argv[0])
os.chdir(LOCALDIR)

try:
    username = '-'+os.getlogin()
except:
    try:
        import pwd
        username = '-'+pwd.getpwuid(os.getuid())[0]
    except:
        username = ''
TAGFILENAME = 'BubBob-%s%s.url' % (socket.gethostname(), username)
TAGFILENAME = os.path.join(tempfile.gettempdir(), TAGFILENAME)


def look_for_local_server():
    # Look for a running local web server
    try:
        url = open(TAGFILENAME, 'r').readline().strip()
    except (OSError, IOError):
        return None
    if not url.startswith('http://127.0.0.1:'):
        return None
    url1 = url[len('http://127.0.0.1:'):]
    try:
        port = int(url1[:url1.index('/')])
    except ValueError:
        return None
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('', port))
    except socket.error:
        return None
    try:
        s.shutdown(2)
        s.close()
    except:
        pass
    return url

def start_local_server():
    if hasattr(os, 'fork') and hasattr(os, 'dup2'):
        if os.fork() == 0:
            # in the child process
            sys.path.append(os.path.join(LOCALDIR, 'bubbob'))
            import bb
            import gamesrv, stdlog
            bb.BubBobGame.Quiet = 1
            logfile = stdlog.LogFile()
            bb.start_metaserver(TAGFILENAME, 0)
            if logfile:
                print >> logfile
                if logfile:
                    print "Logging to", logfile.filename
                    fd = logfile.f.fileno()
                    try:
                        # detach from parent
                        os.dup2(fd, 1)
                        os.dup2(fd, 2)
                        os.dup2(fd, 0)
                    except OSError:
                        pass
                    logfile.close()
            gamesrv.mainloop()
            sys.exit(0)
    else:
        MAINSCRIPT = os.path.abspath(os.path.join(LOCALDIR, 'bubbob', 'bb.py'))
        args = [sys.executable, MAINSCRIPT,
                '--saveurlto=%s' % TAGFILENAME, '--quiet']
        os.spawnv(os.P_NOWAITO, args[0], args)


# main
url = look_for_local_server()
if not url:
    start_local_server()
    # wait for up to 5 seconds for the server to start
    for i in range(10):
        import time
        time.sleep(0.5)
        url = look_for_local_server()
        if url:
            break
    else:
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
    if look_for_local_server() != url:
        # assume that browser.open() waited for the browser to finish
        # and that the server has been closed from the browser.
        raise SystemExit
    print
    print '-'*60
    print "If the browser fails to open the page automatically,"
    print "you will have to manually go to the following URL:"
print ' ', url
print '-'*60
print "Note that the server runs in the background. You have to use"
print "the 'Stop this program' link to cleanly stop it."
print "Normally, however, running this script multiple times should"
print "not create multiple servers in the background."
