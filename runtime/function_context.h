#ifndef FUNCTION_CONTEXT_H
#define FUNCTION_CONTEXT_H

#include <stdio.h>

struct FunctionContext {
  int32_t spill_count;
  FunctionContext* outer;
  int32_t params_size;
};


#endif
