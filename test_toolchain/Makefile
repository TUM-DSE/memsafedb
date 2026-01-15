all: test_mte test_cheri

test_mte: mte_test.cpp
	clang++ -march=armv8.5-a+memtag mte_test.cpp -o test_mte

test_cheri: main.cpp
	$(MORELLO_HOME)/llvm/bin/clang++ -march=morello -mabi=purecap -Wcheri --target=aarch64-linux-musl_purecap -DCHERI --sysroot $(MUSL_HOME) -nostdlib -static -L$(MORELLO_HOME)/musl/lib -L$(MORELLO_HOME)/gnu/lib/gcc/aarch64-none-linux-gnu/10.1.0/purecap/c64 $(MORELLO_HOME)/musl/lib/crt1.o $(MORELLO_HOME)/musl/lib/crti.o -g main.cpp -lc++ -lunwind -lc++abi -lc -L$(MORELLO_HOME)/llvm/lib/clang/14.0.0/lib/aarch64-unknown-linux-musl_purecapi -lgcc $(MORELLO_HOME)/musl/lib/crtn.o -o test_cheri
	
bench_aarch64: bench_cheri.cpp
	clang++ -stdlib=libc++ -march=native -L/tmp -I../utils -I$(LIBCXX_HDR)/include/c++/v1/ -L$(MUSL_PATH)/lib -static -nostdlib $(MUSL_PATH)/lib/crt1.o $(MUSL_PATH)/lib/crti.o -g bench_cheri.cpp -lc++ -lunwind -lc++abi -Wl,--start-group -lc -lgcc -Wl,--end-group $(MUSL_PATH)/lib/crtn.o -o bench_aarch64 

bench_cheri: bench_cheri.cpp
	$(MORELLO_HOME)/llvm/bin/clang++ -march=morello -mabi=purecap -Wcheri --target=aarch64-linux-musl_purecap -DCHERI -I../utils --sysroot $(MUSL_HOME) -nostdlib -static -L$(MORELLO_HOME)/musl/lib -L$(MORELLO_HOME)/gnu/lib/gcc/aarch64-none-linux-gnu/10.1.0/purecap/c64 $(MORELLO_HOME)/musl/lib/crt1.o $(MORELLO_HOME)/musl/lib/crti.o -g bench_cheri.cpp -lc++ -lunwind -lc++abi -lc -L$(MORELLO_HOME)/llvm/lib/clang/14.0.0/lib/aarch64-unknown-linux-musl_purecapi -lgcc $(MORELLO_HOME)/musl/lib/crtn.o -o bench_cheri
