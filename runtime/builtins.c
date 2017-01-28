#include <stdio.h>

void builtin_write(void** function_context) {
  int value = (int) function_context[3];
  printf("%d\n", value);
}
