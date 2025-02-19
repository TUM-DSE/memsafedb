
#ifdef __x86_64__
.intel_syntax noprefix
#endif

.global benchmark

benchmark:
#ifdef __x86_64__
        test    rdx, rdx
        je      .LBB0_3
        dec     rsi
        xor     eax, eax
.LBB0_2:
        mov     rcx, rax
        and     rcx, rsi

        // test the write operation
        mov     dword ptr [rdi + 4*rcx], 0

        inc     rax
        cmp     rdx, rax
        jne     .LBB0_2
.LBB0_3:
        ret
#else
#error "We currently only support x86 architecture"
#endif
