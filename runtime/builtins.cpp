#include "memory.h"

#include <stdio.h>

extern "C" void builtin_write(void** function_context, int* stack_low, int* stack_high) {
  int value = (int) function_context[3];
  printf("%d\n", value);
}

extern "C" void* builtin_Array(void** function_context, int* stack_low, int* stack_high) {
  fprintf(stderr, "Calling builtin_Array, %p %p\n", stack_low, stack_high);
  int size = (int) function_context[3];
  // FIXME: magic number
  void* array = memory_allocate(size * sizeof(int), stack_low, stack_high);
  fprintf(stderr, "Array of size %d is %p\n", size, array);
  return array;
}
