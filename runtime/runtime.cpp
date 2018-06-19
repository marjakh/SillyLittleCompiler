#include "constants.h"
#include "function_context.h"
#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

extern "C" void user_code();

extern "C" FunctionContext* runtime_CreateFunctionContext(void* outer, std::int32_t params_and_locals_count, int return_value_count, int* stack_low) {
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate(sizeof(FunctionContext) + (params_and_locals_count + return_value_count) * POINTER_SIZE, stack_low));
  context->outer = reinterpret_cast<FunctionContext*>(outer);
  context->spill_count = 0; // Caller fills this in
  context->params_and_locals_count = params_and_locals_count;
  context->return_value_count = return_value_count;
  fprintf(stderr, "CreateFunctionContext (outer %p) returns %p\n", outer, context);
  return context;
}

extern "C" FunctionContext* runtime_CreateMainFunctionContext(std::int32_t locals_count) {
  // We don't have proper stack structure yet, so GC cannot
  // happen. But we're guaranteed to have enough space in the start.
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate_no_gc(sizeof(FunctionContext) + locals_count * POINTER_SIZE));
  context->outer = nullptr;
  context->spill_count = 0; // Caller fills this in
  context->params_and_locals_count = locals_count;
  context->return_value_count = 0;
  fprintf(stderr, "CreateMainFunctionContext returns %p\n", context);
  return context;
}

extern "C" void runtime_SetStackHigh(std::int32_t* stack_high) {
  memory_set_stack_high(stack_high);
}

int main(int argc, char** argv) {
  memory_init();
  fprintf(stderr, "Calling user code\n");
  user_code();
  fprintf(stderr, "User code returned\n");
  memory_teardown();
  fprintf(stderr, "Runtime exiting\n");
  return 0;
}
