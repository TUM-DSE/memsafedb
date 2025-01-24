# This Makefile can be used for local development. For benchmarking on MTE supported devices please use the
# CMakeList and benchmark.sh in the appropriate directories.
CC = gcc
CFLAGS = -O3 -g

line:
	$(CC) $(CFLAGS) -o line main.c

simple:
	$(CC) $(CFLAGS) -o simple simple.c

clean:
	rm -f line 
