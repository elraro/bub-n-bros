all: bb.py.html bb.py.txt Client.py.html Client.py.txt BubBob.py.html BubBob.py.txt compress

compress: bb.py.1.gz Client.py.1.gz BubBob.py.1.gz

%.html : %.1
	groff -man -Thtml $< > $@

%.txt : %.1
	groff -man -Tascii $< > $@

%.1.gz : %.1
	gzip -c $< > $@

clean:
	rm -f bb.py.txt Client.py.txt BubBob.py.txt
	rm -f bb.py.html Client.py.html BubBob.py.html

install:
	$(INSTALL) -c -o $(MANOWNER) -g $(MANGROUP) -m 644 bb.py.1.gz $(MANDIR)/man1/bubnbros-server.1.gz
	$(INSTALL) -c -o $(MANOWNER) -g $(MANGROUP) -m 644 Client.py.1.gz $(MANDIR)/man1/bubnbros.1.gz
	$(INSTALL) -c -o $(MANOWNER) -g $(MANGROUP) -m 644 BubBob.py.1.gz $(MANDIR)/man1/BubBob.1.gz

	### TODO: install for html and txt files!
