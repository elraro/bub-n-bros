import sys, os

try:
    ThisDir = __file__
except NameError:
    ThisDir = os.getcwd()
ThisDir = os.path.dirname(ThisDir)

### rotate colors
import colorsys
COLORS = [#(0, 0.0, 1.0, 1, 1),      # vert
          #(1, 0.0, 1.0, 1, 1),      # bleu
          (1, -0.7, 1.0, 1, 1),      # rose
          (0, -0.2, 1.0, 1, 1),      # brun
          (1,  0.72,1.0,-1, 1),      # jaune
          (0, -0.35,0.85,1, 1),      # rouge
          (0,   0,  0.0, 1, 1),      # gris
          #(0, 0.93, 0.9,-1, 1),      # bleu marine
          (0, 0.5,  0.9, 1, 1),      # mauve
          #(0, 0.2,  1.0, 1, 1),      # turquoise
          (0, 0.92, 1.0,-1, 1),       # bleu fonce
          #(0, 0.45, 0.5, -0.5, 0.75), # hum
          (1, 'specialpixelmap'),
          ]


def inputfiles():
    InputFiles = {
        os.path.join(ThisDir, os.pardir, 'ext1', 'image1-%d.ppm'): 1,
        os.path.join(ThisDir, os.pardir, 'ext3', 'image1-%d.ppm'): 1,
        os.path.join(ThisDir, os.pardir, 'ext4', 'image1-%d.ppm'): 1,
        }
    d = {}
    execfile(os.path.join(ThisDir, os.pardir, 'sprmap.py'), d)
    sprmap = d['sprmap']
    for key, (filename, rect) in sprmap.items():
        if filename.find('%d') >= 0:
            InputFiles[os.path.join(ThisDir, filename)] = 1
    InputFiles = InputFiles.keys()
    InputFiles.sort()
    return InputFiles

# ____________________________________________________________

def pixelmap(rgb1, rgb2):
    if rgb1 == rgb2:
        return rgb1
    r, g, b = rgb1
    r /= 255.0
    g /= 255.0
    b /= 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h*sign + delta) % 1.0
    s *= sat
    v *= lumen
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return r*255.1, g*255.1, b*255.1

def specialpixelmap(rgb1, rgb2):
    if rgb1 == rgb2:
        return rgb1
    r, g, b = rgb1
    return r * 0.2, g * 0.8, r * 0.6

def ppmbreak(f):
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
    return w, h, data

def rotate(imglist, chr=chr, int=int, ord=ord):
    global delta, sat, sign, lumen
    (bw, bh, blue), (gw, gh, green) = imglist
    assert bw == gw and bh == gh
    for reserved in range(len(COLORS)):
        if len(COLORS[reserved]) == 2:
            n, fn = COLORS[reserved]
            fn = globals()[fn]
        else:
            n, delta, sat, sign, lumen = COLORS[reserved]
            fn = pixelmap
        (_, _, fromimage) = imglist[n]
        (_, _, otherimage) = imglist[1-n]
        image = []
        for i in range(0, len(fromimage), 3):
            rgb1 = ord(fromimage[i]), ord(fromimage[i+1]), ord(fromimage[i+2])
            rgb2 = ord(otherimage[i]),ord(otherimage[i+1]),ord(otherimage[i+2])
            r, g, b = fn(rgb1, rgb2)
            image.append(chr(int(r))+chr(int(g))+chr(int(b)))
        imglist.append((bw, bh, ''.join(image)))

def writeout(imglist, namepattern):
    for i in range(2, len(imglist)):
        w, h, data = imglist[i]
        fn = namepattern % i
        f = open(fn, 'wb')
        print >> f, 'P6'
        print >> f, w, h
        print >> f, 255
        f.write(data)
        f.close()


def convert(name):
    imglist = [ppmbreak(open(name % 0, 'rb')),
               ppmbreak(open(name % 1, 'rb'))]
    rotate(imglist)
    writeout(imglist, name)


if __name__ == '__main__':
    try:
        import psyco; psyco.full()
    except:
        pass

    for filename in inputfiles():
        print >> sys.stderr, 'generating colors for %s...' % filename
        convert(filename)
