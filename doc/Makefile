all: bb.py.html bb.py.txt Client.py.html Client.py.txt BubBob.py.html BubBob.py.txt

%.html : %.1
	groff -man -Thtml $< > $@

%.txt : %.1
	groff -man -Tascii $< > $@

clean:
	rm -f *.txt
	rm -f *.html
