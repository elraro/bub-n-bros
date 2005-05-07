OWNER=root
GROUP=games
LIBDIR=/usr/local/lib
BINDIR=/usr/local/games

MANOWNER=root
MANGROUP=root
MANDIR=/usr/local/man

INSTALL=install

all: docs
	make -C bubbob
	make -C display

clean:
	-rm -f `find -name "*~"`
	-rm -f `find -name "*.py[co]"`
	-rm -fr `find -name "build"`
	make -C doc clean

sync: magma-sync codespeak-sync

magma-sync:
	rsync --delete -avz -e ssh ~/games/* magma:games/x/

codespeak-sync:
	rsync --delete -avz -e ssh ${HOME}/games/metaserver ${HOME}/games/common codespeak.net:games/

meta:
	ssh codespeak.net python games/metaserver/metaserver.py -f

docs:
	make -C doc

# crude install
install:
#	make -C doc install
# install fanciness not yet implemented :)
#	make -C bubbob install
#	make -C display install	
	$(INSTALL) -d $(LIBDIR)/bub-n-bros
	cp -R . $(LIBDIR)/bub-n-bros
	chown -R $(OWNER):$(GROUP) $(LIBDIR)/bub-n-bros
	sed -ie '/__OVERRIDE__/ s:^#\(.*\)__OVERRIDE__\(.*\):\1$(LIBDIR)/bub-n-bros/display/Client.py\2:' \
		$(LIBDIR)/bub-n-bros/display/Client.py
	ln -s $(LIBDIR)/bub-n-bros/display/Client.py $(BINDIR)/bubnbros
	echo -e "#!/bin/sh \n\
		cd $(LIBDIR)/bub-n-bros/bubbob/; exec env python bb.py $$@" > $(BINDIR)/bubnbros-server
	chmod +x $(BINDIR)/bubnbros-server
