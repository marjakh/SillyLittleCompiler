#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

void* runtime_allocate(int size) {
  // FIXME: gc
  void* v = malloc(size);
  return v;
}
