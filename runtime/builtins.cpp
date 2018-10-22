#include "constants.h"
#include "memory.h"
#include "tagging.h"

#include <stdio.h>

extern "C" void builtin_write(void** tagged_function_context, int* stack_low) {
  int32_t* function_context = untag_pointer(tagged_function_context);
  int32_t value = reinterpret_cast<int32_t>(function_context[FUNCTION_CONTEXT_PARAMS_OFFSET]);
  value = untag_int(value);
  printf("%d\n", value);
}

extern "C" void* builtin_Array(void** tagged_function_context, int* stack_low) {
  fprintf(stderr, "Calling builtin_Array, %p\n", stack_low);
  int32_t* function_context = untag_pointer(tagged_function_context);
  int32_t size = reinterpret_cast<int32_t>(function_context[FUNCTION_CONTEXT_PARAMS_OFFSET]);
  size = untag_int(size);
  int32_t* array = memory_allocate(size * sizeof(int), stack_low);
  fprintf(stderr, "Array of size %d is %p\n", size, array);
  return tag_pointer(array);
}

extern "C" void* builtin_test_do_gc(void** tagged_function_context, int* stack_low) {
  memory_test_do_gc(stack_low);
  return nullptr;
}

extern "C" void* builtin_test_is_live_object(void** tagged_function_context, int* stack_low) {
  int32_t* function_context = untag_pointer(tagged_function_context);
  int32_t* object = reinterpret_cast<int32_t*>(function_context[FUNCTION_CONTEXT_PARAMS_OFFSET]);
  object = untag_pointer(object);
  return reinterpret_cast<void*>(memory_test_is_live_object(object));
}
