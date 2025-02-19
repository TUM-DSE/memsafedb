
#ifdef __x86_64__
.intel_syntax noprefix
#endif

.global benchmark

benchmark:
#ifdef __x86_64__
        test    rsi, rsi
        je      .LBB1_3
        lea     rax, [rsi - 1]
        xor     ecx, ecx
.LBB1_2:
        mov     r8, rcx
        and     r8, rax
        inc     dword ptr [rdi + 4*r8]
        add     rcx, rdx
        dec     rsi
        jne     .LBB1_2
.LBB1_3:
        ret
#elif __aarch64__
        cbz     x1, .END
        mov     x8, xzr
.LOOP:
        // Compute address manually, because ldg (load tag from memory) does not support complex addressing
        mov     x10, x8
        lsl     x10, x10, #2    // x10 = x8 * 4
        add     x10, x10, x0    // x10 = base + offset

#ifdef MTE
        ldg     x9, [x10]  
#else
        ldr     w9, [x10]
#endif

        add     x8, x8, x2
        cmp     x8, x1
        b.lo    .LOOP
.END:
        ret
#else
#error "We only support x86 and aarch64 architecture"
#endif
