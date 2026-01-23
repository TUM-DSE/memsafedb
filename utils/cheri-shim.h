/* cheri-shim.h */
#ifndef CHERI_SHIM_H
#define CHERI_SHIM_H

#include <stdlib.h>

#define strtoll_l(n, e, b, l)   strtoll(n, e, b)
#define strtoull_l(n, e, b, l)  strtoull(n, e, b)
#define strtof_l(n, e, l)       strtof(n, e)
#define strtod_l(n, e, l)       strtod(n, e)
#define strtold_l(n, e, l)      strtold(n, e)

#endif // CHERI_SHIM_H
