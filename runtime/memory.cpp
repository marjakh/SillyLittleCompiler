#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

#include <set>

#define CHUNK_SIZE 4096

#define COLOR_WHITE 0
#define COLOR_GREY 0
#define COLOR_BLACK 0

// FIXME: this simple version has only one memory chunk. Use a list instead.
// FIXME: zap memory which has been freed.

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
  if (current_chunk_cursor + size + 2 < current_chunk_end) {
    fprintf(stderr, "Fits in the current chunk\n");
    // Reserve space for size and color.
    // FIXME: compact; no need to use 8 bytes for them. Also add helpers.
    result = current_chunk_cursor + 2;
    std::int32_t* p = (std::int32_t*)current_chunk_cursor;
    *p = size;
    *(p + 1) = COLOR_WHITE;
    current_chunk_cursor += (size + 2);
  } else {
    // Collect garbage.
    fprintf(stderr, "GC starting\n");
    do_gc(stack_low, stack_high);
    fprintf(stderr, "GC done\n");
    // FIXME: try again, maybe we can allocate now.
  }

  return result;
}

void mark_and_sweep(std::set<std::pair<int32_t**, int32_t*>>* ptrs) {
  // Iterate through known objects.
  for (const auto& ptr_pair : *ptrs) {
    int32_t** location_on_stack = ptr_pair.first;
    int32_t* ptr = ptr_pair.second;

    fprintf(stderr, "Visiting object %p\n", ptr);

    
    // Mark the object grey.
    *(ptr - 1) = COLOR_GREY;

    // Move this (root object) into the new space.

    
    // Update the value of the pointer in the stack.
  }

  // FIXME: How to mark all objects white again?
}

void do_gc(std::int32_t* stack_low, std::int32_t* stack_high) {
  // Discover potential pointers. They can be in the stack or in the current
  // memory chunk, pointed to by already discovered pointers.
  int32_t* p;
  std::set<std::pair<int32_t**, int32_t*>> roots;

  fprintf(stderr, "stack %p %p\n", stack_low, stack_high);

  for (p = stack_low; p < stack_high; ++p) {
    fprintf(stderr, "%p: %p\n", (void*)p, (void*)*p);
    int32_t* maybe_ptr = reinterpret_cast<int32_t*>(*p);
    if (is_in_current_chunk(maybe_ptr)) {
      // FIXME: Is this always a pointer? Do we need to know something more
      // complicated about the structure of the stack?
      fprintf(stderr, "Found pointer %p\n", maybe_ptr);
      roots.insert(std::make_pair(reinterpret_cast<int32_t**>(p), maybe_ptr));
    }
  }

  mark_and_sweep(&roots);
}
