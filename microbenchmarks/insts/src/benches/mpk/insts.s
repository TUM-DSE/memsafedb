.intel_syntax noprefix
.text

// Helper: repeat a 0 operand instruction 16 times
.macro REP16 inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
    \inst
.endm


// rdi = iteration count (number of instructions to execute)
// return value is ignored on the Rust side
// Simple baseline: 16 adds per loop
.global clktest
clktest:
1:
    test    rdi, rdi
    jz      2f
    sub     rdi, 16

    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1
    add     rax, 1

    jmp     1b
2:
    ret


// Generic throughput loop for 0 operand instructions
// name: function name
// inst: instruction mnemonic
.macro GEN_0OP_TP name, inst
    .global \name
\name:
    // Set up scratch registers once
    xor     eax, eax
    xor     ecx, ecx
    xor     edx, edx

1:
    test    rdi, rdi
    jz      2f
    sub     rdi, 16

    REP16   \inst

    jmp     1b
2:
    ret
.endm

// Throughput for RDPKRU and WRPKRU
// Iteration count must be divisible by 16
GEN_0OP_TP rdpkru_throughput_loop, rdpkru
GEN_0OP_TP wrpkru_throughput_loop, wrpkru


// Latency style loop for PKRU roundtrip
// We chain rdpkru -> xor -> wrpkru so each pair depends on the previous state.
// This gives you the cost of one "read PKRU, flip one bit, write PKRU" sequence.
//
// Iteration count is number of pairs, must be divisible by 8.
.global pkru_roundtrip_latency_loop
pkru_roundtrip_latency_loop:
    xor     eax, eax
    xor     ecx, ecx
    xor     edx, edx

1:
    test    rdi, rdi
    jz      2f
    sub     rdi, 8

    .rept   8
        rdpkru         // EAX = current PKRU
        add eax, 0
        wrpkru         // write new PKRU
    .endr

    jmp     1b
2:
    ret
