import cStringIO

def decodepixmap(data):
    f = cStringIO.StringIO(data)
    sig = f.readline().strip()
    assert sig == "P6"
    while 1:
        line = f.readline().strip()
        if not line.startswith('#'):
            break
    wh = line.split()
    w, h = map(int, wh)
    sig = f.readline().strip()
    assert sig == "255"
    data = f.read()
    f.close()
    return w, h, data

def encodepixmap(w, h, data):
    return 'P6\n%d %d\n255\n%s' % (w, h, data)

def vflip(w, h, data):
    scanline = w*3
    lines = [data[p:p+scanline] for p in range(0, len(data), scanline)]
    lines.reverse()
    return ''.join(lines)

def makebkgnd(w, h, data):
    scanline = 3*w
    result = []
    for position in range(0, scanline*h, scanline):
        line = []
        for p in range(position, position+scanline, 3):
            line.append(2 * (chr(ord(data[p  ]) >> 3) +
                             chr(ord(data[p+1]) >> 3) +
                             chr(ord(data[p+2]) >> 3)))
        line = ''.join(line)
        result.append(line)
        result.append(line)
    return w*2, h*2, ''.join(result)
