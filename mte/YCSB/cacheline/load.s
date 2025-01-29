.intel_syntax noprefix
.global benchmark


benchmark:
  sub     rsi, 1

  xor     ecx, ecx

  test    rdx, rdx
  je      .L1
.L3:
  mov     rax, rcx

  add     rcx, 1
  sal     rax, 4
  and     rax, rsi

  add     DWORD PTR [rdi+rax*4], 1
  cmp     rdx, rcx
  jne     .L3
.L1:
  ret




