# This Makefile can be used for local development. For benchmarking on MTE supported devices please use the
# CMakeList and benchmark.sh in the appropriate directories.
CC = gcc
CFLAGS = -O3

line:
	$(CC) $(CFLAGS) -o line main.c

simple:
	$(CC) $(CFLAGS) -o simple simple.c load.s

loadonly:
	$(CC) $(CFLAGS) -o loadonly simple.c load_only.S

storeonly:
	$(CC) $(CFLAGS) -o storeonly simple.c write_only.S

clean:
	rm -f line simple loadonly storeonly
