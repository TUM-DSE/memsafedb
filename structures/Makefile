# Designed by Cristian Sandu <cristian.sandu@tum.de>
# Converted for clang-morello by Cristian Sandu

CC            = clang
CXX           = clang++
CFLAGS        = -fpic -shared
# architecture-specific flags, e.g. morello flags when on morello
ARCH_FLAGS    =
# linker flags
LDFLAGS       =
CMAKE_FLAGS   =
CMAKE         = cmake

# All binaries
ALL =  libclht_gc libclht_lb libclht_lb.a clht_lb libclht_lf libclht_lf.a clht_lf \
	   libclht_lf_res libclht_lf_res.a clht_lf_res cuckoo stdlib tbb
all: $(ALL)

ENABLE_MORELLO ?= false

ifeq ($(ENABLE_MORELLO), true)
	ARCH_FLAGS += $(MORELLO_FLAGS)
	CC = clang-morello
	CXX = clang++-morello
	LDFLAGS = -Wl,-z,now -Wl,-z,relro
	CMAKE_FLAGS = -DCMAKE_C_COMPILER=$(CC) -DCMAKE_CXX_COMPILER=$(CXX) -DCMAKE_CXX_FLAGS="-march=morello -mabi=purecap -Xclang -morello-vararg=new"
endif

# CLHT section
CLHT_PATH     = ./CLHT
CLHT_INCLUDE  = -I$(CLHT_PATH)/include -I$(CLHT_PATH)/external/include
CLHT_SRC      = $(CLHT_PATH)/src
CLHT_LIBS     = -L$(CLHT_PATH)/external/lib -L. -lrt -lpthread -lm
CLHT_BMARK    = clht.c
CLHT_FLAGS    = $(CFLAGS) -D_GNU_SOURCE -DADD_PADDING -DDEFAULT -O3

libclht_gc:
	$(CC) $(ARCH_FLAGS) $(CLHT_INCLUDE) -o libclht_gc.o -c $(CLHT_SRC)/clht_gc.c

libclht_lb:
	$(CC) $(CLHT_FLAGS) $(ARCH_FLAGS) $(CLHT_INCLUDE) $(CLHT_SRC)/clht_lb.c -o libclht_lb.o

libclht_lb.a: libclht_gc libclht_lb
	@echo Archive name = libclht_lb.a
	rm -f  libclht_lb.a
	ar -r libclht_lb.a libclht_lb.o libclht_gc.o

clht_lb: libclht_lb.a
	$(CC) -DNO_RESIZE -DCLHT_LB $(CLHT_FLAGS) $(ARCH_FLAGS) $(CLHT_INCLUDE) $(CURDIR)/libclht_lb.o $(CURDIR)/libclht_gc.o $(CLHT_BMARK) -o clht_lb.so $(CLHT_LIBS) -lclht_lb -lssmem

libclht_lf:
	$(CC) $(ARCH_FLAGS) $(CLHT_INCLUDE) -o libclht_lf.o -c $(CLHT_SRC)/clht_lf.c

libclht_lf.a: libclht_gc libclht_lf
	@echo Archive name = libclht_lf.a
	rm -f libclht_lf.a
	ar -r libclht_lf.a libclht_lf.o libclht_gc.o

clht_lf: libclht_lf.a
	$(CC) -DLOCKFREE -DCLHT_LF $(ARCH_FLAGS) $(CLHT_INCLUDE) $(CLHT_BMARK) -o clht_lf.so $(CLHT_LIBS) -lclht_lf -lssmem

libclht_lf_res:
	$(CC) $(CLHT_FLAGS) $(ARCH_FLAGS) $(CLHT_INCLUDE) $(CLHT_SRC)/clht_lf_res.c -o libclht_lf_res.o

libclht_lf_res.a: libclht_lf_res.o libclht_gc.o
	@echo Archive name = libclht_lf.a
	rm -f  libclht_lf.a
	ar -r libclht_lf.a libclht_lf_res.o libclht_gc.o

clht_lf_res:
	$(CC) -DLOCKFREE_RES -DCLHT_LF $(CLHT_FLAGS) $(ARCH_FLAGS) $(CLHT_INCLUDE) $(CURDIR)/libclht_lf_res.o $(CURDIR)/libclht_gc.o $(CLHT_BMARK) -o clht_lf_res.so $(CLHT_LIBS) -lclht_lf -lssmem


# libcuckoo section
LIBCUCKOO_INSTALL_PATH = ./libcuckoo/install
LIBCUCKOO_INCLUDE := -I$(LIBCUCKOO_INSTALL_PATH)
LIBCUCKOO_PATH = ./libcuckoo

libcuckoo:
	$(CMAKE) $(CMAKE_FLAGS) -S $(LIBCUCKOO_PATH) -B $(LIBCUCKOO_PATH)/build -DCMAKE_INSTALL_PREFIX=$(LIBCUCKOO_PATH)/install -DCMAKE_BUILD_TYPE=Release
	$(CMAKE) --build $(LIBCUCKOO_PATH)/build -$j(nproc) -- install

cuckoo: libcuckoo
	   $(CC) $(CFLAGS) $(ARCH_FLAGS) $(LIBCUCKOO_INCLUDE) cuckoo.cpp -o cuckoo.so $(LDFLAGS)


# art section
ART_PATH 	= -I./adaptive-radix-tree/include
art:
		$(CC) $(ARCH_FLAGS) $(ART_PATH) art.cpp -o art.so

# cuckootrie section
CUCKOOTRIE_PATH  = ./cuckoo-trie-code
CUCKOOTRIE_IPATH = -I$(CUCKOOTRIE_PATH)
# TODO: why is libcuckoo_trie.so not used here?
LIB_SOURCES = $(CUCKOOTRIE_PATH)/main.c $(CUCKOOTRIE_PATH)/util.c \
			  $(CUCKOOTRIE_PATH)/verify_trie.c $(CUCKOOTRIE_PATH)/random.c \
			  $(CUCKOOTRIE_PATH)/atomics.c $(CUCKOOTRIE_PATH)/mt_debug.c
CUCKOOTRIE_FLAGS =

$(CUCKOOTRIE_PATH)/libcuckoo_trie.so:
	$(MAKE) -C $(CUCKOOTRIE_PATH)

cuckootrie: $(CUCKOOTRIE_PATH)/libcuckoo_trie.so
	cp $(CUCKOOTRIE_PATH)/libcuckoo_trie.so .
	# TODO: check if this works, and if yes, remove LIB_SOURCES
	#$(CC) $(ARCH_FLAGS) $(CUCKOOTRIE_IPATH) $(CUCKOOTRIE_FLAGS) -DNDEBUG cuckootrie.c -o cuckootrie.so $(LIB_SOURCES) -pthread
	$(CC) $(ARCH_FLAGS) $(CUCKOOTRIE_IPATH) $(CUCKOOTRIE_FLAGS) -DNDEBUG cuckootrie.c -o cuckootrie.so $(CUCKOOTRIE_PATH)/libcuckoo_trie.so -pthread


stdlib:
	$(CC) $(ARCH_FLAGS) -lstdc++ stdlib.cpp -o stdlib.so


# tbb section
TBB_PATH := ./oneTBB
TBB_INCLUDE := -I$(TBB_PATH)/include
TBB_LDLIBS = -L $(TBB_PATH)/build/lib -ltbb

libtbb:
	$(CMAKE) $(CMAKE_FLAGS) -S $(TBB_PATH) -B $(TBB_PATH)/build -DCMAKE_INSTALL_PREFIX=$(TBB_PATH)/install -DCMAKE_BUILD_TYPE=Release
	$(CMAKE) --build $(TBB_PATH)/build -$j(nproc) -- install

tbb: libtbb
	$(CC) $(ARCH_FLAGS) $(TBB_INCLUDE) $(TBB_LDLIBS) tbb.cpp -o tbb.so

clean:
	rm -f *.so *.a *.o
