all:
	make -C bubbob
	make -C display

clean:
	-rm -f `find -name "*~"`
	-rm -f `find -name "*.py[co]"`
	-rm -fr `find -name "build"`

sync: magma-sync codespeak-sync

magma-sync:
	rsync --delete -avz -e ssh ~/games/* magma:games/x/

codespeak-sync:
	rsync --delete -avz -e ssh ${HOME}/games/metaserver ${HOME}/games/common codespeak.net:games/
