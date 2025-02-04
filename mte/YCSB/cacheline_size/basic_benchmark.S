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
#else
#error "We only support x86 architecture"
#endif
