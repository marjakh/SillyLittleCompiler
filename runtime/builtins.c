#include "memory.h"

#include <stdio.h>

void builtin_write(void** function_context) {
  int value = (int) function_context[3];
  printf("%d\n", value);
}

void* builtin_Array(void** function_context) {
  int size = (int) function_context[3];
  return runtime_allocate(size);
}
