#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

#define CHUNK_SIZE 4096

// FIXME: this simple version has only one memory chunk. Use a list instead.
char* current_chunk = 0;
char* current_chunk_cursor = 0;
char* current_chunk_end = 0;

char* other_chunk = 0;
char* other_chunk_cursor = 0;
char* other_chunk_end = 0;

// FIMXE: intptr_t?
bool is_in_current_chunk(void* p) {
  return p > current_chunk && p < current_chunk_end;
}

void memory_init() {
  current_chunk = reinterpret_cast<char*>(malloc(CHUNK_SIZE));
  current_chunk_cursor = current_chunk;
  current_chunk_end = current_chunk + CHUNK_SIZE;
  fprintf(stderr, "First chunk: %p %p\n", current_chunk_cursor, current_chunk_end);

  other_chunk = reinterpret_cast<char*>(malloc(CHUNK_SIZE));
}

void memory_teardown() {
  free(current_chunk);
  free(other_chunk);
}

void do_gc(std::int32_t* stack_low, std::int32_t* stack_high);

// FIXME: stack_high is always the same, no need to pass it more than once.
void* memory_allocate(std::int32_t size, std::int32_t* stack_low, std::int32_t* stack_high) {
  fprintf(stderr, "Allocate %d\n", size);

  void* result = 0;
  if (current_chunk_cursor + size < current_chunk_end) {
    fprintf(stderr, "Fits in the current chunk\n");
    result = current_chunk_cursor + 1;
    std::int32_t* p = (std::int32_t*)current_chunk_cursor;
    *p = size;
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

void do_gc(std::int32_t* stack_low, std::int32_t* stack_high) {
  // Discover potential pointers. They can be in the stack or in the current
  // memory chunk, pointed to by already discovered pointers.
  std::int32_t* p;

  fprintf(stderr, "stack %p %p\n", stack_low, stack_high);

  for (p = stack_low; p < stack_high; ++p) {
    fprintf(stderr, "%p: %p\n", (void*)p, (void*)*p);
    if (is_in_current_chunk((void*)*p)) {
      // FIXME: Is this always a pointer? Do we need to know something more
      // complicated about the structure of the stack?
      fprintf(stderr, "Found pointer %p\n", (void*)*p);
    }
  }

}
