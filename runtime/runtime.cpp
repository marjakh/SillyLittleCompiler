#include "memory.h"
#include "function_context.h"

#include <stdio.h>
#include <stdlib.h>

extern "C" void user_code(void*);

extern "C" void* runtime_GetGlobalsTable(int globals_size, int* stack_low, int* stack_high) {
  void* v = memory_allocate(4 * globals_size, stack_low, stack_high);
  fprintf(stderr, "GetGlobalsTable %d returns %p\n", globals_size, v);
  return v;
}

// FIXME: get rid of params_size, need to change the caller side too.
extern "C" FunctionContext* runtime_CreateFunctionContext(int32_t spill_count, void* outer, int32_t params_size, int* stack_low, int* stack_high) {
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate(sizeof(FunctionContext), stack_low, stack_high));
  context->spill_count = spill_count;
  context->outer = reinterpret_cast<FunctionContext*>(outer);
  fprintf(stderr, "CreateFunctionContext returns %p\n", context);
  return context;
}

int main(int argc, char** argv) {
  memory_init();
  // Create a FunctionContext (for user main) and pass it to user_code.
  FunctionContext* function_context = runtime_CreateFunctionContext(0, nullptr, 0, nullptr, nullptr);
  fprintf(stderr, "Calling user code\n");
  user_code(function_context);
  fprintf(stderr, "User code returned\n");
  memory_teardown();
  fprintf(stderr, "Runtime exiting\n");
  return 0;
}
