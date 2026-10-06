# Bug-class suite: one runner binary per configuration.
#
#   baseline   plain build (reference: what happens without protection)
#   mte        Arm MTE, glibc tagging (run with GLIBC_TUNABLES=glibc.mem.tagging=3)
#   cheri      CHERI purecap (Morello, musl)
#
# baseline/mte build with the eliza (or cross-compiler) devshell, cheri with
# the cross-compiler devshell (MORELLO_* variables).

SRC = runner.c bugs.c
HDR = bugs.h
BUILD = build

# make predefines CC=cc; default to clang unless CC is given explicitly.
ifeq ($(origin CC),default)
CC = clang
endif
# -O1 keeps the bugs intact (volatile accesses); -fno-builtin stops the compiler
# from eliding malloc/free pairs or stores into freed memory; no stack protector so stack
# overflows are attributed to the mechanism under test only; no _FORTIFY_SOURCE
# (the nix compiler wrapper enables it) so libc checks do not preempt the mechanism.
CFLAGS_COMMON = -O1 -g -std=gnu11 -Wall -Wextra -fno-stack-protector -fno-builtin \
                -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 \
                -fno-omit-frame-pointer

# The nix cc-wrapper injects -D_FORTIFY_SOURCE on its own; drop that hardening.
export NIX_HARDENING_ENABLE := $(filter-out fortify fortify3,$(NIX_HARDENING_ENABLE))

# MTE: use the MTE-enabled glibc (GLIBC_MTE is set by the eliza devshell).
MTE_CFLAGS = -march=armv8.5-a+memtag -DMTE
ifneq ($(GLIBC_MTE),)
MTE_LDFLAGS = -Wl,--dynamic-linker=$(GLIBC_MTE)/lib/ld-linux-aarch64.so.1
endif

# CHERI purecap, statically linked against the purecap musl (as for SQLite).
CHERI_CC = $(MORELLO_CLANG_DIR)/bin/clang -nostartfiles -nodefaultlibs
CHERI_CFLAGS = -march=morello -mabi=purecap --target=aarch64-linux-musl_purecap \
               --sysroot=$(MORELLO_SYSROOT)
CHERI_LDFLAGS = $(MORELLO_SYSROOT)/lib/crt1.o $(MORELLO_SYSROOT)/lib/crti.o \
                -L$(MORELLO_LLVM_DIR)/lib -L$(MORELLO_LLVM_DIR)/lib/linux \
                -L$(MORELLO_SYSROOT)/lib -static -fuse-ld=lld -lc \
                -lclang_rt.builtins-aarch64 $(MORELLO_SYSROOT)/lib/crtn.o

.PHONY: all host clean
host: baseline mte
all: baseline mte cheri

baseline: $(BUILD)/runner_baseline
mte: $(BUILD)/runner_mte
cheri: $(BUILD)/runner_cheri

$(BUILD):
	mkdir -p $@

$(BUILD)/runner_baseline: $(SRC) $(HDR) | $(BUILD)
	$(CC) $(CFLAGS_COMMON) -o $@ $(SRC)

$(BUILD)/runner_mte: $(SRC) $(HDR) | $(BUILD)
	$(CC) $(CFLAGS_COMMON) $(MTE_CFLAGS) $(MTE_LDFLAGS) -o $@ $(SRC)

$(BUILD)/runner_cheri: $(SRC) $(HDR) | $(BUILD)
	$(CHERI_CC) $(CFLAGS_COMMON) $(CHERI_CFLAGS) -o $@ $(SRC) $(CHERI_LDFLAGS)

clean:
	rm -rf $(BUILD)
