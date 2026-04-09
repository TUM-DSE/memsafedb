#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/prctl.h>

int main(int argc, char **argv) {
    if (argc != 2) return 1;

    unsigned long ctrl = PR_TAGGED_ADDR_ENABLE | PR_MTE_TCF_SYNC | (0xfffeUL << PR_MTE_TAG_SHIFT);
    prctl(PR_SET_TAGGED_ADDR_CTRL, ctrl, 0, 0, 0);

    // 32MB
    size_t size = 32 * 1024 * 1024;
    void *buf = mmap(NULL, size, PROT_READ | PROT_WRITE | PROT_MTE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    memset(buf, 0, size);

    int op = atoi(argv[1]);
    uint64_t zero = 0;

    for (int i = 0; i < 500; i++) {
        unsigned char *p = buf;
        unsigned char *end = p + size;

        if (op == 1) {
            memset(buf, 0, size);
        } else if (op == 2) {
            while (p < end) {
                __asm volatile("stzg %0, [%0], #16" : "+r"(p) : : "memory");
            }
        } else if (op == 3) {
            while (p < end) {
                __asm volatile("stgp xzr, xzr, [%0], #16" : "+r"(p) : : "memory");
            }
        } else if (op == 4) {
            while (p < end) {
                __asm volatile("stnp %1, %1, [%0]" : "+r"(p) : "r"(zero) : "memory");
                p += 16;
            }
        } else if (op == 5) {
            while (p < end) {
                __asm volatile("stp xzr, xzr, [%0], #16" : "+r"(p) : : "memory");
            }
        }
    }

    munmap(buf, size);
    return 0;
}
