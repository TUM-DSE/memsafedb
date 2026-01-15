/* cheri-shim.h */
#ifndef CHERI_SHIM_H
#define CHERI_SHIM_H

/* 1. Include the system stdlib first.
      This ensures standard types and functions (strtoll, strtod) are declared 
      BEFORE we start hacking macros. This prevents the "conflicting types" error. */
#include <stdlib.h>

/* 2. Map missing locale functions to standard functions.
      Since we included stdlib.h above, these macros won't break the 
      declarations inside it. */
#define strtoll_l(n, e, b, l)   strtoll(n, e, b)
#define strtoull_l(n, e, b, l)  strtoull(n, e, b)
#define strtof_l(n, e, l)       strtof(n, e)
#define strtod_l(n, e, l)       strtod(n, e)
#define strtold_l(n, e, l)      strtold(n, e)

#endif // CHERI_SHIM_H
