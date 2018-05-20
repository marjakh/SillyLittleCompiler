#ifndef RUNTIME_FUNCTION_CONTEXT_H
#define RUNTIME_FUNCTION_CONTEXT_H

#include <stdio.h>

struct FunctionContext {
  FunctionContext* outer;
  int32_t spill_count;
  int32_t params_size;
  int32_t locals_size;
};


#endif
