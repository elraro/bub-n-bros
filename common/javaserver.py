from __future__ import nested_scopes
import sys, os
from cStringIO import StringIO


INDEX_PAGE = '''<html>
<head><title>%(title)s</title></head>
<body><h1>%(title)s</h1>
 <applet code=pclient.class width=%(width)s height=%(height)s>
  <param name="gameport" value="%(gameport)d">
 </applet>
</body>
</html>
'''


def setup(bkgnd=1, httpport=8000, **kw):
    indexdata = INDEX_PAGE % kw

    def indexloader():
        return StringIO(indexdata), 'text/html'

    dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'java'))
    if not os.path.isdir(dir):
        return 0
    sys.path.insert(0, dir)
    import httpserver

    # register all '.class' files
    for name in os.listdir(dir):
        if name.endswith('.class'):
            httpserver.register(name, httpserver.fileloader(os.path.join(dir, name)))

    # register a '' and an 'index.html' file
    httpserver.register('', indexloader)
    httpserver.register('index.html', indexloader)

    return httpserver.runserver(bkgnd, httpport)
