#include <stdio.h>
#include <stdlib.h>

extern void user_code(void);

void* runtime_GetGlobalsTable(int globals_size) {
  // FIXME: gc
  void* v = malloc(4 * globals_size);
  printf("GetGlobalsTable %d returns %p\n", globals_size, v);
  return v;
}

void* runtime_CreateFunctionContext(void* previous, void* outer, int params_size) {
  // FIXME: gc
  void** context = (void**)malloc(4 * (3 + params_size));
  context[0] = previous;
  context[1] = outer;
  context[2] = 0;
  printf("CreateFunctionContext %d %p returns %p\n", params_size, previous, context);
  return context;
}

int main(int argc, char** argv) {
  printf("Runtime starting\n");
  user_code();
  printf("Runtime exiting\n");
  return 0;
}
