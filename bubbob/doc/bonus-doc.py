#!/usr/bin/env python

import os, sys, string, struct
os.chdir(os.pardir)
sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.pardir, 'common')))

from images import sprmap
import bonuses, images

try:
    import psyco; psyco.full()
except ImportError:
    pass

def create_image(name,source,extralines=0):
    if len(sys.argv) == 2 and sys.argv[1] == '-i':
        return
    print name, source
    src = open(source[0],'r')
    assert src.readline().strip() == 'P6'
    line = src.readline()
    while line[0] == '#':
        line = src.readline()
    size = string.split(line)
    w = string.atoi(size[0])
    h = string.atoi(size[1])
    c = src.readline().strip()
    data = src.read()
    src.close()
    img = os.popen("convert PPM:- doc/images/"+name+'.png','w')
    print >> img, 'P6'
    print >> img, source[1][2], source[1][3]+extralines
    print >> img, c
    cx = source[1][0]+source[1][2]//2
    cy = source[1][1]+source[1][3]*6//7
    for y in range(source[1][1],source[1][1]+source[1][3]):
        for x in range(source[1][0],source[1][0]+source[1][2]):
            rgb = data[y*3*w+3*x:y*3*w+3*x+3]
            if rgb == '\x01\x01\x01':
                d = (x-cx)*(x-cx)+(y-cy)*(y-cy)*6
                if d > 255: d = 255
                rgb = chr(d)*3
            img.write(rgb)
    for y in range(y+1, y+1+extralines):
        for x in range(source[1][0],source[1][0]+source[1][2]):
            d = (x-cx)*(x-cx)+(y-cy)*(y-cy)*6
            if d > 255: d = 255
            rgb = chr(d)*3
            img.write(rgb)
    img.close()
    
def split_name(name):
    "Split a name into its words based on capitalisation."
    words = []
    word = ''
    for c in name:
        if c.isupper() and word != '':
            words.append(word)
            word = c
        else:
            word += c
    words.append(word)
    return words

dfile = open('doc/bonuses.html','w')
print >> dfile, """<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<HTML>
 <HEAD>
  <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=iso-8859-1">
  <META NAME="Author" CONTENT="The Bub's Brothers">
  <TITLE>The Bub's Brothers Bonuses</TITLE>
 </HEAD>
 <BODY bgcolor=white text=black>
  <TABLE>
"""
#" A stupid comment to stop emacs from mis-fontifying.

# Some classes exists in more than one example just to increase their
# probability. Removes the duplicate with the help of this dict.
processed = {}

for bonus in bonuses.Classes:
    if processed.has_key(bonus):
        continue
    name = split_name(bonus.__name__)
    name.reverse()
    processed[bonus] = string.join(name)

def sorter(a,b):
    if a[1] == b[1]:
        return 0
    elif a[1] < b[1]:
        return -1
    else:
        return 1

sorted_classes = processed.items()
sorted_classes.sort(sorter)

for clas in sorted_classes:
    bonus = clas[0]
    images = ''
    name = bonus.__name__
    if bonus.__dict__.has_key('nimages'):
        # A multi image entry.
        i = 0
        l = len(bonus.nimages)
        for image in bonus.nimages:
            create_image(name+`i`, sprmap[image])
            images += '<IMG SRC="images/%s%d.png" ALT="%s">' % (name,i,name)
            i += 1
            if (l-3*(i/3) >= 3) and (i % 3) == 0:
                images += '<br>'
    elif bonus.__dict__.has_key('nimage'):
        create_image(name,sprmap[bonus.nimage])
        images = '<IMG SRC="images/%s.png" ALT="%s">' % (name,name)
    doc = bonus.__doc__
    if doc == None:
        doc = ''
    print >> dfile, '<TR><TD width=132 align=right>',
    print >> dfile, images,
    print >> dfile, '</TD><TD width=20></TD><TD>',doc,'</TD></TR>'

print >> dfile, """  </TABLE>
 </BODY>
</HTML>
"""

dfile.close()
