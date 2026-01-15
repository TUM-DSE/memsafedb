ifeq ($(ARCH),)
ARCH="aarch64"
endif

UNAME := $(shell uname -n)

ifeq ($(ARCH), aarch64)
ifeq ($(UNAME), ace)
CXX = clang++
CXXFLAGS += -static -stdlib=libc++ -I$(LIBCXX_HDR)/include/c++/v1/ -L$(MUSL_PATH)/lib -nostdlib $(MUSL_PATH)/lib/crt1.o $(MUSL_PATH)/lib/crti.o -DAARCH64_ACE -Wno-unused-command-line-argument 
LDFLAGS += -lc++ -lunwind -lc++abi -Wl,--start-group -lc -lgcc -Wl,--end-group -lboost_system -lboost_thread -L/tmp $(MUSL_PATH)/lib/crtn.o
else
CXX = g++
LDFLAGS = -lboost_system -lboost_thread
endif
endif

ifeq ($(ARCH), mte)
CXXFLAGS = -I../../utils
CXXFLAGS += -march=armv8.5-a+memtag -DMTE
endif

ifeq ($(ARCH), cheri)
ifeq ($(MORELLO_HOME),)
$(error "Please source /morello/env/morello-sdk first")
endif
CXX = $(MORELLO_HOME)/llvm/bin/clang++
CXXFLAGS = -g -O0 -march=morello -mabi=purecap -Wcheri --target=aarch64-linux-musl_purecap -DCHERI --sysroot $(MUSL_HOME)
CXXFLAGS += -nostdlib -static -L$(MORELLO_HOME)/musl/lib -L$(MORELLO_HOME)/gnu/lib/gcc/aarch64-none-linux-gnu/10.1.0/purecap/c64
CXXFLAGS += $(MORELLO_HOME)/musl/lib/crt1.o $(MORELLO_HOME)/musl/lib/crti.o -I$(MORELLO_HOME)/boost/boost_1_89_0 -I$(MORELLO_HOME)/usr/include
LDFLAGS = -lc++ -lunwind -lc++abi -lc -L$(MORELLO_HOME)/llvm/lib/clang/14.0.0/lib/aarch64-unknown-linux-musl_purecap -lgcc $(MORELLO_HOME)/musl/lib/crtn.o
endif

queue_bench: main.cpp
	$(CXX) -DNDEBUG -O3 -std=c++17 -g $(CXXFLAGS) main.cpp -o queue_bench $(LDFLAGS)

clean:
	rm -f queue_bench
