#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

extern void user_code(void);

void* runtime_GetGlobalsTable(int globals_size) {
  void* v = runtime_allocate(4 * globals_size);
  fprintf(stderr, "GetGlobalsTable %d returns %p\n", globals_size, v);
  return v;
}

void* runtime_CreateFunctionContext(void* previous, void* outer, int params_size) {
  void** context = (void**)runtime_allocate(4 * (3 + params_size));
  context[0] = previous;
  context[1] = outer;
  context[2] = 0;
  fprintf(stderr, "CreateFunctionContext %d %p returns %p\n", params_size, previous, context);
  return context;
}

int main(int argc, char** argv) {
  int stack_is_here = 0;
  memory_init(&stack_is_here);
  user_code();
  memory_teardown();
  fprintf(stderr, "Runtime exiting\n");
  return 0;
}
