CC = gcc
CFLAGS = -O3
CFLAGS += -Wa,--noexecstack

default:
	make clean
	make cache_size_load
	make cache_size_write
	./benchmark.sh

cache_size_load:
	$(CC) $(CFLAGS) -o cache_size_load \
		main.c \
		../allocator/allocator.c  \
		load_only.S

cache_size_write:
	$(CC) $(CFLAGS) -o cache_size_write \
		main.c \
		../allocator/allocator.c  \
		write_only.S

clean:
	rm -f cache_size_load cache_size_write 
