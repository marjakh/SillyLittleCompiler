#ifndef RUNTIME_FUNCTION_CONTEXT_H
#define RUNTIME_FUNCTION_CONTEXT_H

#include <cstdint>

struct FunctionContext {
  FunctionContext* outer;
  int32_t spill_count;
  int32_t params_and_locals_count;
};


#endif
