#include "memory.h"

#include <stdio.h>

extern "C" void builtin_write(void** function_context, int* stack_low, int* stack_high) {
  int32_t value = (int32_t) function_context[3];
  printf("%d\n", value);
}

extern "C" void* builtin_Array(void** function_context, int* stack_low, int* stack_high) {
  fprintf(stderr, "Calling builtin_Array, %p %p\n", stack_low, stack_high);
  int32_t size = (int32_t) function_context[3];
  // FIXME: magic number
  void* array = memory_allocate(size * sizeof(int), stack_low, stack_high);
  fprintf(stderr, "Array of size %d is %p\n", size, array);
  return array;
}

extern "C" void* builtin_test_do_gc(void** function_context, int* stack_low, int* stack_high) {
  memory_test_do_gc(stack_low, stack_high);
  return nullptr;
}

extern "C" void* builtin_test_is_live_object(void** function_context, int* stack_low, int* stack_high) {
  int32_t* object = (int32_t*) function_context[3];
  return reinterpret_cast<void*>(memory_test_is_live_object(object));
}
