#ifndef FUNCTION_CONTEXT_H
#define FUNCTION_CONTEXT_H

#include <stdio.h>

struct FunctionContext {
  int32_t spill_count;
  FunctionContext* outer;
  int32_t whats_this; // FIXME: Some legacy stuff, remove this from both sides.
  int32_t param;
};


#endif
