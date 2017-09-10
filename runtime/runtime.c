#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

extern void user_code(void);

void* runtime_GetGlobalsTable(int globals_size, int* stack_low, int* stack_high) {
  void* v = memory_allocate(4 * globals_size, stack_low, stack_high);
  fprintf(stderr, "GetGlobalsTable %d returns %p\n", globals_size, v);
  return v;
}

void* runtime_CreateFunctionContext(void* previous, void* outer, int params_size, int* stack_low, int* stack_high) {
  void** context = (void**)memory_allocate(4 * (3 + params_size), stack_low, stack_high);
  context[0] = previous;
  context[1] = outer;
  context[2] = 0;
  fprintf(stderr, "CreateFunctionContext %d %p returns %p\n", params_size, previous, context);
  return context;
}

int main(int argc, char** argv) {
  memory_init();
  user_code();
  memory_teardown();
  fprintf(stderr, "Runtime exiting\n");
  return 0;
}
