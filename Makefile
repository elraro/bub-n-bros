all:
	make -C bubbob
	make -C display

clean:
	-rm -f `find -name "*~"`
	-rm -f `find -name "*.py[co]"`
	-rm -fr `find -name "build"`
