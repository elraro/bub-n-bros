#! /usr/bin/env python
import sys, os

try:
    ThisDir = __file__
except NameError:
    ThisDir = os.getcwd()
else:
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
          (0, 0.5,  0.9, 1, 1),      # mauve
          #(0, 0.2,  1.0, 1, 1),      # turquoise
          (0, 0.925, 0.95,-1, 1),       # bleu fonce
          #(0, 0.45, 0.5, -0.5, 0.75), # hum
          (1, 'specialpixelmap'),    # vert fonce
          ]
MAX = 2+len(COLORS)

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
    return InputFiles.keys()

# ____________________________________________________________

def pixelmap(r, g, b):
    r /= 255.0
    g /= 255.0
    b /= 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h*sign + delta) % 1.0
    s *= sat
    v *= lumen
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return r*255.1, g*255.1, b*255.1

def specialpixelmap(r, g, b):
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

COLORMAPS = [{} for n in COLORS]
del n

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
        colormap = COLORMAPS[reserved]
        append = image.append
        for i in range(0, len(fromimage), 3):
            rgb1 = fromimage[i:i+3]
            rgb2 = otherimage[i:i+3]
            if rgb1 == rgb2:
                append(rgb1)
            elif rgb1 in colormap:
                append(colormap[rgb1])
            else:
                r, g, b = fn(ord(rgb1[0]), ord(rgb1[1]), ord(rgb1[2]))
                newrgb = chr(int(r))+chr(int(g))+chr(int(b))
                append(newrgb)
                colormap[rgb1] = newrgb
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
    print >> sys.stderr, 'generating colors for %s...' % name
    imglist = [ppmbreak(open(name % 0, 'rb')),
               ppmbreak(open(name % 1, 'rb'))]
    rotate(imglist)
    writeout(imglist, name)

def updatecheck():
    myself = os.path.join(ThisDir, 'buildcolors.py')

    def older(list1, list2):
        def mtime(name):
            try:
                st = os.stat(name)
            except OSError:
                return None
            else:
                return st.st_mtime
        list2 = [mtime(name) for name in list2]
        if None in list2:
            return 0
        else:
            list1 = [mtime(name) for name in list1]
            list1 = [t for t in list1 if t is not None]
            return list1 and list2 and max(list1) < min(list2)

    rebuild = {}
    for filename in inputfiles():
        distfiles = [myself, filename % 0, filename % 1]
        genfiles = [filename % n for n in range(2, MAX)]
        rebuild[filename] = not older(distfiles, genfiles)
    return rebuild


if __name__ == '__auto__':    # when execfile'd from images.py
    rebuild = updatecheck().items()
    rebuild.sort()
    for fn, r in rebuild:
        if r:
            convert(fn)

if __name__ == '__main__':
    try:
        import psyco; psyco.full()
    except:
        pass

    if sys.argv[1:2] == ['-f']:
        files = inputfiles()
    elif sys.argv[1:2] == ['-c']:
        for filename in inputfiles():
            for n in range(2, MAX):
                print 'rm', filename % n
                os.unlink(filename % n)
        sys.exit()
    else:
        rebuild = updatecheck()
        if 0 in rebuild.values():
            print >> sys.stderr, ('%d images up-to-date. '
                                  'Use -f to force a rebuild or -c to clean.' %
                                  rebuild.values().count(0))
        files = [fn for fn, r in rebuild.items() if r]

    files.sort()
    for filename in files:
        convert(filename)
