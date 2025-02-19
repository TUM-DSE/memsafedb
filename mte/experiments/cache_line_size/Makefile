CC = gcc
CFLAGS = -O3
CFLAGS += -Wa,--noexecstack

default:
	make clean
	make cache_line_size_load
	./benchmark.sh

cache_line_size_load:
	$(CC) $(CFLAGS) -o cache_line_size_load \
		main.c \
		../allocator/allocator.c  \
		load_only.S

clean:
	rm -f cache_line_size_load
