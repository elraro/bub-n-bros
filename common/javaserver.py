import sys, os
from cStringIO import StringIO
import httpserver

EMPTY_PAGE = '''<html>
<head><title>No server is running</title></head>
<body><h1>No server is running at the moment.</h1>
</body>
</html>
'''

INDEX_PAGE = '''<html>
<head><title>%(title)s</title></head>
<body><h1>%(title)s</h1>
 <applet code=pclient.class width=%(width)s height=%(height)s>
  <param name="gameport" value="%(gameport)d">
 </applet>
</body>
</html>
'''

def indexloader(**options):
    import gamesrv
    if gamesrv.game is None:
        indexdata = EMPTY_PAGE
    else:
        indexdata = INDEX_PAGE % {
            'title':    gamesrv.game.FnDesc,
            'width':    gamesrv.game.width,
            'height':   gamesrv.game.height,
            'gameport': gamesrv.game.address[1],
            }
    return StringIO(indexdata), 'text/html'

wave_cache = {}

def wav2au(data):
    # Very limited! Assumes a standard 8-bit mono .wav as input
    import audioop, struct
    freq, = struct.unpack("<i", data[24:28])
    data = data[44:]
    data = audioop.bias(data, 1, -128)
    data, ignored = audioop.ratecv(data, 1, 1, freq, 8000, None)
    data = audioop.lin2ulaw(data, 1)
    data = struct.pack('>4siiiii8s',
                       '.snd',                         # header
                       struct.calcsize('>4siiiii8s'),  # header size
                       len(data),                      # data size
                       1,                              # encoding
                       8000,                           # sample rate
                       1,                              # channels
                       'magic.au') + data
    return data

def sampleloader(code=[], **options):
    import gamesrv
    try:
        data = wave_cache[code[0]]
    except KeyError:
        for key, snd in gamesrv.samples.items():
            if str(getattr(snd, 'code', '')) == code[0]:
                data = wave_cache[code[0]] = wav2au(snd.read())
                break
        else:
            raise KeyError, code[0]
    return StringIO(data), 'audio/wav'


def setup():
    dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       os.pardir,
                                       'java'))
    if not os.path.isdir(dir):
        return

    # register all '.class' files
    for name in os.listdir(dir):
        if name.endswith('.class'):
            httpserver.register(name, httpserver.fileloader(os.path.join(dir, name)))

    # register a '' and an 'index.html' file
    httpserver.register('', indexloader)
    httpserver.register('index.html', indexloader)

    # register the sample loader
    httpserver.register('sample.wav', sampleloader)

setup()
