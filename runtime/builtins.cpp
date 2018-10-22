#include "memory.h"
#include "constants.h"

#include <stdio.h>

extern "C" void builtin_write(void** function_context, int* stack_low) {
  int32_t value = (int32_t) function_context[FUNCTION_CONTEXT_PARAMS_OFFSET] >> INT_TAG_SHIFT;
  printf("%d\n", value);
}

extern "C" void* builtin_Array(void** function_context, int* stack_low) {
  fprintf(stderr, "Calling builtin_Array, %p\n", stack_low);
  int32_t size = (int32_t) function_context[FUNCTION_CONTEXT_PARAMS_OFFSET] >> INT_TAG_SHIFT;
  void* array = memory_allocate(size * sizeof(int), stack_low);
  fprintf(stderr, "Array of size %d is %p\n", size, array);
  return array;
}

extern "C" void* builtin_test_do_gc(void** function_context, int* stack_low) {
  memory_test_do_gc(stack_low);
  return nullptr;
}

extern "C" void* builtin_test_is_live_object(void** function_context, int* stack_low) {
  int32_t* object = (int32_t*) function_context[FUNCTION_CONTEXT_PARAMS_OFFSET];
  return reinterpret_cast<void*>(memory_test_is_live_object(object));
}
