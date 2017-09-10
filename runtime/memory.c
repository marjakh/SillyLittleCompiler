#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

#define CHUNK_SIZE 4096

// FIXME: this simple version has only one memory chunk. Use a list instead.
void* current_chunk = 0;
void* current_chunk_cursor = 0;
void* current_chunk_end = 0;

void* other_chunk = 0;
void* other_chunk_cursor = 0;
void* other_chunk_end = 0;

// FIMXE: intptr_t?
int is_in_current_chunk(void* p) {
  return p > current_chunk && p < current_chunk_end;
}

void memory_init() {
}

void memory_teardown() {
  free(current_chunk);
  free(other_chunk);
}

void do_gc(int* stack_low, int* stack_high);

// FIXME: stack_high is always the same, no need to pass it more than once.
void* memory_allocate(int size, int* stack_low, int* stack_high) {
  fprintf(stderr, "Allocate %d\n", size);
  if (current_chunk == 0) {
    // First allocation.
    current_chunk = malloc(CHUNK_SIZE);
    current_chunk_cursor = current_chunk;
    current_chunk_end = current_chunk + CHUNK_SIZE;
    fprintf(stderr, "First chunk: %p %p\n", current_chunk_cursor, current_chunk_end);

    void* other_chunk = malloc(CHUNK_SIZE);
  }

  void* result = 0;
  if (current_chunk_end - current_chunk_cursor > size) {
    fprintf(stderr, "Fits in the current chunk\n");
    result = current_chunk_cursor + 1;
    void** p = (void**)current_chunk_cursor;
    *p = (void*)size;
    current_chunk_cursor += (size + 1);
  } else {
    // Collect garbage.
    fprintf(stderr, "GC starting\n");
    do_gc(stack_low, stack_high);
    fprintf(stderr, "GC done\n");
    // FIXME: try again, maybe we can allocate now.
  }

  return result;
}

void do_gc(int* stack_low, int* stack_high) {
  // Discover potential pointers. They can be in the stack or in the current
  // memory chunk, pointed to by already discovered pointers.
  int* p;

  fprintf(stderr, "stack %p %p\n", stack_low, stack_high);

  for (p = stack_low; p < stack_high; ++p) {
    fprintf(stderr, "%p: %p\n", (void*)p, (void*)*p);
    if (is_in_current_chunk((void*)*p)) {
      fprintf(stderr, "Found pointer %p\n", (void*)*p);
    }
  }

}
