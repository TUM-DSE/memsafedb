
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
#ifdef __aarch64__
        cmp     x1, #0
        beq     .LBB1_3
        sub     x0, x1, #1
        mov     x2, #0
.LBB1_2:
        mov     x8, x2
        and     x8, x0, x8

        ldr     w9, [x0, x8, lsl #2]  // Load value

        add     x2, x2, x3
        sub     x1, x1, #1
        cbnz    x1, .LBB1_2
.LBB1_3:
        ret
#else
#error "We only support x86 and aarch64 architecture"
#endif
