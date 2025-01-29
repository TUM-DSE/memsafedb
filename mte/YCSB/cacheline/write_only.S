#ifdef __x86_64__
.intel_syntax noprefix
#endif

.global benchmark


benchmark:
#ifdef __x86_64__
  sub     rsi, 1

  xor     ecx, ecx

  test    rdx, rdx
  je      .L1
.L3:
  mov     rax, rcx

  add     rcx, 1
  sal     rax, 4
  and     rax, rsi

  mov     DWORD PTR [rdi + rax * 4], 0

  cmp     rdx, rcx
  jne     .L3
.L1:
  ret
#endif

#ifdef __aarch64__
  cbz     x2, .LBB0_3
  mov     x8, xzr

  mov     w11, xrz

  sub     x9, x1, #1
.LBB0_2:
  and     x10, x8, x9
  subs    x2, x2, #1
  add     x8, x8, #16

  str     w11, [x0, x10, lsl #2]

  b.ne    .LBB0_2
.LBB0_3:
  ret

#endif
