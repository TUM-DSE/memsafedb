# designed by Cristian Sandu <cristian.sandu@tum.de>

GCC    = gcc
CFLAGS = -fPIC -shared -pg -ggdb3 -fno-omit-frame-pointer

# all binaries
ALL =  libclht_gc libclht_lb libclht_lb.a clht_lb libclht_lf libclht_lf.a clht_lf \
	   libclht_lf_res libclht_lf_res.a clht_lf_res cuckoo
all: $(ALL)

# CLHT section
CLHT_PATH 	 = /scratch/christian/cheridb/structures/CLHT
CLHT_INCLUDE = -I$(CLHT_PATH)/include -I$(CLHT_PATH)/external/include
CLHT_SRC 	 = $(CLHT_PATH)/src
CLHT_LIBS 	 = -L$(CLHT_PATH)/external/ssmem -L. -lrt -lpthread -lm
CLHT_BMARK   = clht.c
CLHT_FLAGS   = $(CFLAGS) -D_GNU_SOURCE -DADD_PADDING -DDEFAULT -O3

libclht_gc:
	$(GCC) $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CLHT_SRC)/clht_gc.c -o libclht_gc.o

libclht_lb:
	$(GCC) $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CLHT_SRC)/clht_lb.c -o libclht_lb.o

libclht_lb.a: libclht_lb.o libclht_gc.o
	@echo Archive name = libclht_lb.a
	ar -d libclht_lb.a *
	ar -r libclht_lb.a libclht_lb.o libclht_gc.o


clht_lb: libclht_lb.a
	$(GCC) -DNO_RESIZE -DCLHT_LB $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CURDIR)/libclht_lb.o $(CURDIR)/libclht_gc.o $(CLHT_BMARK) -o clht_lb.so $(CLHT_LIBS) -lclht_lb -lssmem

libclht_lf:
	$(GCC) $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CLHT_SRC)/clht_lf.c -o libclht_lf.o

libclht_lf.a: libclht_lf.o libclht_gc.o
	@echo Archive name = libclht_lf.a
	ar -d libclht_lf.a *
	ar -r libclht_lf.a libclht_lf.o libclht_gc.o

clht_lf:
	$(GCC) -DLOCKFREE -DCLHT_LF $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CURDIR)/libclht_lf.o $(CURDIR)/libclht_gc.o $(CLHT_BMARK) -o clht_lf.so $(CLHT_LIBS) -lclht_lf -lssmem

libclht_lf_res:
	$(GCC) $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CLHT_SRC)/clht_lf_res.c -o libclht_lf_res.o

libclht_lf_res.a: libclht_lf_res.o libclht_gc.o
	@echo Archive name = libclht_lf.a
	ar -d libclht_lf.a *
	ar -r libclht_lf.a libclht_lf_res.o libclht_gc.o

clht_lf_res:
	$(GCC) -DLOCKFREE_RES -DCLHT_LF $(CLHT_FLAGS) $(CLHT_INCLUDE) $(CURDIR)/libclht_lf_res.o $(CURDIR)/libclht_gc.o $(CLHT_BMARK) -o clht_lf_res.so $(CLHT_LIBS) -lclht_lf -lssmem


# libcuckoo section
LIBCUCKOO_INCLUDE := -Ilibcuckoo
LIBCUCKOO_PATH = /scratch/christian/cheridb/structures/libcuckoo

cuckoo:
	$(GCC) $(CFLAGS) $(LIBCUCKOO_INCLUDE) cuckoo.cpp -o cuckoo.so


# tbb section
TBB_INCLUDE := -Ilibcuckoo
TBB_PATH = /scratch/christian/cheridb/structures/libcuckoo

cuckoo:
	$(GCC) $(CFLAGS) $(LIBCUCKOO_INCLUDE) cuckoo.cpp -o cuckoo.so

clean:
	rm -f *.so *.a *.o
