#include "memory.h"
#include "function_context.h"

#include <stdio.h>
#include <stdlib.h>

extern "C" void user_code();

extern "C" FunctionContext* runtime_CreateFunctionContext(void* outer, std::int32_t spill_count, std::int32_t params_size, std::int32_t locals_size, int* stack_low) {
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate(sizeof(FunctionContext) + (params_size + locals_size) * 4, stack_low));
  context->outer = reinterpret_cast<FunctionContext*>(outer);
  context->spill_count = spill_count;
  context->params_size = params_size;
  context->locals_size = locals_size;
  fprintf(stderr, "CreateFunctionContext returns %p\n", context);
  return context;
}

extern "C" FunctionContext* runtime_CreateMainFunctionContext(std::int32_t spill_count, std::int32_t locals_size) {
  // We don't have proper stack structure yet, so GC cannot happen. But we're guaranteed to have enough space in the start.
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate_no_gc(sizeof(FunctionContext) + locals_size * 4));
  context->outer = nullptr;
  context->spill_count = spill_count;
  context->params_size = 0;
  context->locals_size = locals_size;
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
