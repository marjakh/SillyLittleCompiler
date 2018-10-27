#include "constants.h"
#include "errors.h"
#include "function_context.h"
#include "memory.h"
#include "tagging.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char* error_messages[] = {"Array index not an int",
                                "Array base not an array"};

extern "C" void user_code();

extern "C" void* runtime_CreateFunctionContext(std::int32_t* outer, std::int32_t params_and_locals_count, int return_value_count, int* stack_low) {
  assert(has_pointer_tag(outer));
  // If the allocation causes GC, it will invalidate "outer".
  TemporaryHandle outer_handle(outer);
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate(sizeof(FunctionContext) + (params_and_locals_count + return_value_count) * POINTER_SIZE, stack_low));
  context->outer = reinterpret_cast<FunctionContext*>(outer_handle.tagged_ptr());
  context->spill_count = 0; // Caller fills this in
  context->params_and_locals_count = params_and_locals_count;
  context->return_value_count = return_value_count;
  fprintf(stderr, "CreateFunctionContext (outer %p) returns %p\n", outer, context);
  return tag_pointer(context);
}

extern "C" void* runtime_CreateFunction(FunctionContext* function_context, std::int32_t* code_address, std::int32_t params_and_locals_count, int* stack_low) {
  // If the allocation causes GC, it will invalidate "outer".
  TemporaryHandle function_context_handle(reinterpret_cast<std::int32_t*>(function_context));
  Function* function = reinterpret_cast<Function*>(memory_allocate(sizeof(Function), stack_low));
  function->function_context = reinterpret_cast<FunctionContext*>(function_context_handle.tagged_ptr());
  assert(has_pointer_tag(function->function_context));
  function->code_address = code_address;
  function->return_value_offset = sizeof(FunctionContext) + params_and_locals_count * POINTER_SIZE;
  fprintf(stderr, "CreateFunction (FunctionContext %p) returns %p\n", function_context, function);
  return tag_pointer(function);
}

extern "C" void* runtime_CreateMainFunctionContext(std::int32_t locals_count) {
  // We don't have proper stack structure yet, so GC cannot
  // happen. But we're guaranteed to have enough space in the start.
  FunctionContext* context = reinterpret_cast<FunctionContext*>(memory_allocate_no_gc(sizeof(FunctionContext) + locals_count * POINTER_SIZE));
  context->outer = nullptr;
  context->spill_count = 0; // Caller fills this in
  context->params_and_locals_count = locals_count;
  context->return_value_count = 0;
  fprintf(stderr, "CreateMainFunctionContext returns %p\n", context);
  return tag_pointer(context);
}

extern "C" void runtime_SetStackHigh(std::int32_t* stack_high) {
  memory_set_stack_high(stack_high);
}

extern "C" void runtime_Error(int32_t error_index) {
  terminate_with_runtime_error(error_messages[error_index]);
}

int main(int argc, char** argv) {
  if (argc >= 2 && strcmp(argv[1], "--gc-stress") == 0) {
    memory_test_set_gc_stress();
  }
  memory_init();
  fprintf(stderr, "Calling user code\n");
  user_code();
  fprintf(stderr, "User code returned\n");
  memory_teardown();
  fprintf(stderr, "Runtime exiting\n");
  return 0;
}
