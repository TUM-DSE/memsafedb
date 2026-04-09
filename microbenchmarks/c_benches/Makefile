COMMON_SOURCES = main.c
PTRCHASE_SRC   = ptr_chase.c
MEMCPY_SRC     = memcpy.c
MEMSET_SRC     = memset.c
MEMREAD_SRC    = memread.c
LDXR_STXR_SRC  = cheri_ldxr_stxr.c
ATOMIC_PTR_TABLE_SRC = atomic_ptr_table.c
DB_NODE_SRC = cheri_db_node.c
HEADERS        = ptr_chase.h

CFLAGS_SHARED = -O3 -std=c11 -Wall -Wextra -march=armv8.5-a+memtag
CFLAGS = $(CFLAGS_SHARED) -static
LDFLAGS = -lm
CHERI_CFLAGS = --target=aarch64-unknown-linux-musl_purecap -mabi=purecap -march=morello -fuse-ld=lld -nostdinc --sysroot ${MUSL_PATH}/ -isystem ${MUSL_PATH}/include -L${MUSL_PATH}/lib -I"${LLVM_PATH}/lib/clang/15.0.0/include"
CHERI_HYBRID_CFLAGS = -O3 -std=c11 -Wall -Wextra -march=morello
PTHREAD_LDFLAGS = -pthread

all: ptr_chase_purecap ptr_chase_normal memcpy_purecap memcpy_normal memset_purecap memset_normal memread_purecap memread_normal mte_caches cheri_caches cheri_narrow_bounds cheri_db_node mte_alloc cheri_ptr_eq stzg_vs_memset cheri_ldxr_stxr atomic_ptr_table_purecap atomic_ptr_table_normal

ptr_chase_purecap: $(COMMON_SOURCES) $(PTRCHASE_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ $(COMMON_SOURCES) $(PTRCHASE_SRC) $(LDFLAGS)

ptr_chase_normal: $(COMMON_SOURCES) $(PTRCHASE_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG) $(CFLAGS) -o build/$@ $(COMMON_SOURCES) $(PTRCHASE_SRC) $(LDFLAGS)

memcpy_purecap: $(COMMON_SOURCES) $(MEMCPY_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ $(COMMON_SOURCES) $(MEMCPY_SRC) $(LDFLAGS)

memcpy_normal: $(COMMON_SOURCES) $(MEMCPY_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG) $(CFLAGS) -o build/$@ $(COMMON_SOURCES) $(MEMCPY_SRC) $(LDFLAGS)

memset_purecap: $(COMMON_SOURCES) $(MEMSET_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ $(COMMON_SOURCES) $(MEMSET_SRC) $(LDFLAGS)

memset_normal: $(COMMON_SOURCES) $(MEMSET_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG) $(CFLAGS) -o build/$@ $(COMMON_SOURCES) $(MEMSET_SRC) $(LDFLAGS)

memread_purecap: $(COMMON_SOURCES) $(MEMREAD_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ $(COMMON_SOURCES) $(MEMREAD_SRC) $(LDFLAGS)

memread_normal: $(COMMON_SOURCES) $(MEMREAD_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG) $(CFLAGS) -o build/$@ $(COMMON_SOURCES) $(MEMREAD_SRC) $(LDFLAGS)

atomic_ptr_table_purecap: $(COMMON_SOURCES) $(ATOMIC_PTR_TABLE_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ $(COMMON_SOURCES) $(ATOMIC_PTR_TABLE_SRC) $(LDFLAGS) $(PTHREAD_LDFLAGS)

atomic_ptr_table_normal: $(COMMON_SOURCES) $(ATOMIC_PTR_TABLE_SRC) $(HEADERS)
	mkdir -p build
	$(CLANG) $(CFLAGS) -o build/$@ $(COMMON_SOURCES) $(ATOMIC_PTR_TABLE_SRC) $(LDFLAGS) $(PTHREAD_LDFLAGS)

mte_caches: mte_caches.c
	mkdir -p build
	$(CLANG) $(CFLAGS) -o build/$@ mte_caches.c $(LDFLAGS)

cheri_caches: cheri_caches.c
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ cheri_caches.c $(LDFLAGS)

cheri_narrow_bounds: cheri_narrow_bounds.c
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@_baseline $< $(LDFLAGS)
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ -Xclang -cheri-bounds=subobject-safe -DNARROW_BOUNDS $< $(LDFLAGS)

cheri_db_node: $(DB_NODE_SRC)
	mkdir -p build
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@_baseline $< $(LDFLAGS)
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ -Xclang -cheri-bounds=subobject-safe -DSUBOBJECT_BOUNDS $< $(LDFLAGS)

mte_alloc: mte_alloc.c
	mkdir -p build
	nix develop ../#glibc-mte -c clang $(CFLAGS_SHARED) $(LDFLAGS) -o build/$@ $<

cheri_ptr_eq: cheri_ptr_eq.c
	$(CLANG_PURECAP) -static -std=c11 $(CHERI_CFLAGS) -o build/$@_no_opt $< $(LDFLAGS)
	$(CLANG_PURECAP) $(CFLAGS) $(CHERI_CFLAGS) -o build/$@ $< $(LDFLAGS)


stzg_vs_memset: stzg_vs_memset.c
	$(CLANG) $(CFLAGS) -o build/$@ $< $(LDFLAGS)

cheri_ldxr_stxr: $(LDXR_STXR_SRC)
	mkdir -p build
	$(CLANG_HYBRID) $(CHERI_HYBRID_CFLAGS) -o build/$@ $< $(LDFLAGS)

clean:
	rm -rf build
