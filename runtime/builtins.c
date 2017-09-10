#include "memory.h"

#include <stdio.h>

void builtin_write(void** function_context) {
  int value = (int) function_context[3];
  printf("%d\n", value);
}

void* builtin_Array(void** function_context) {
  int stack_when_entering_runtime = 0;
  int size = (int) function_context[3];
  // FIXME: magic number
  void* array = memory_allocate(size * sizeof(int), &stack_when_entering_runtime);
  fprintf(stderr, "Array of size %d is %p\n", size, array);
  return array;
}
