
drop-caches: drop-caches.c
	cc -o $@ $^
	sudo chown root $@
	sudo chmod u+s $@
	ln -s drop-caches/$@ ../$@.bin

clean:
	rm drop-caches

