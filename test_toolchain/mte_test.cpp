#include <iostream>
#include <cstdlib>
#include <cstdint>
#include <sys/prctl.h>

# define PR_TAGGED_ADDR_ENABLE  (1UL << 0)
# define PR_MTE_TCF_SHIFT       1
# define PR_MTE_TAG_SHIFT       3
# define PR_MTE_TAG_MASK        (0xffffUL << PR_MTE_TAG_SHIFT)

int main() {
  if (prctl(PR_SET_TAGGED_ADDR_CTRL, PR_TAGGED_ADDR_ENABLE | PR_MTE_TCF_SYNC | (0xfffe << PR_MTE_TAG_SHIFT), 0, 0, 0)) {
    perror("prctl() failed");
    return EXIT_FAILURE;
  }

  size_t size = 16;
  char* data = (char*)malloc(sizeof(char)*size);
  data[0] = 'a';
  data[32]='a';
  free(data);
  return 0;
}
