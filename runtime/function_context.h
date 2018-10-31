#ifndef RUNTIME_FUNCTION_CONTEXT_H
#define RUNTIME_FUNCTION_CONTEXT_H

#include <cstdint>

struct FunctionContext {
  FunctionContext* outer;
  int32_t* string_table;
  int32_t spill_count;
  int32_t params_and_locals_count;
  int32_t return_value_count;
};

struct Function {
  FunctionContext* function_context;
  int32_t* code_address;
  int32_t return_value_offset;
};


#endif
