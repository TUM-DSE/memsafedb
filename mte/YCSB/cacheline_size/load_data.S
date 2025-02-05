#ifdef __x86_64__
.intel_syntax noprefix
#endif

.global benchmark


benchmark:
#ifdef __x86_64__
        test    rsi, rsi
        je      .END
        xor     eax, eax
.LOOP:
        mov     r8d, DWORD PTR [rdi + rax * 4] 
        add     rax, rdx
        cmp     rax, rsi
        jb      .LOOP
.END:
        ret
#elif __aarch64__
        cbz     x1, .END
        mov     x8, xzr
.LOOP:

#ifdef COMPLEX_ADDRESSING
        ldr     w9, [x0, x8, lsl #2]

#else 
        // Compute address manually - we dont use complex addressing, so we can compare it with ldg
        mov     x10, x8
        lsl     x10, x10, #2    // x10 = x8 * 4
        add     x10, x10, x0    // x10 = base + offset

        // Load with tag-aware access
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
