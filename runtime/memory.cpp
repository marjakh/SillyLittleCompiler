#include "memory.h"

#include <stdio.h>
#include <stdlib.h>
#include <cassert>
#include <cstring>

#include <stack>
#include <vector>

#define INT_SIZE 4

#define CHUNK_SIZE 4096

#define COLOR_WHITE 0
#define COLOR_GREY 1
#define COLOR_BLACK 2
#define COLOR_MOVED 3

#define ZAP_VALUE 0x41

// FIXME: this simple version has only one memory chunk. Use a list instead.

char* current_chunk = nullptr;
char* current_chunk_cursor = nullptr;
char* current_chunk_end = nullptr;

char* other_chunk = nullptr;
char* other_chunk_cursor = nullptr;
char* other_chunk_end = nullptr;

std::vector<int32_t*>* current_objects;
std::vector<int32_t*>* other_objects;

// FIMXE: intptr_t?
bool is_in_current_chunk(void* p) {
  return p > current_chunk && p < current_chunk_end;
}

int32_t get_color(int32_t* object) {
  return *(object - 1);
}

void set_color(int32_t* object, int32_t color) {
  *(object - 1) = color;
}

int32_t get_byte_size(int32_t* object) {
  return *(object - 2);
}

void set_byte_size(int32_t* object, int32_t size) {
  *(object - 2) = size;
}

void zap_memory(char* memory, size_t size) {
  memset(memory, ZAP_VALUE, size);
}

void memory_init() {
  current_chunk = reinterpret_cast<char*>(malloc(CHUNK_SIZE));
  zap_memory(current_chunk, CHUNK_SIZE);
  current_chunk_cursor = current_chunk;
  current_chunk_end = current_chunk + CHUNK_SIZE;
  fprintf(stderr, "First chunk: %p %p\n", current_chunk_cursor, current_chunk_end);

  other_chunk = reinterpret_cast<char*>(malloc(CHUNK_SIZE));
  other_chunk_cursor = other_chunk;
  other_chunk_end = other_chunk + CHUNK_SIZE;
  zap_memory(current_chunk,  CHUNK_SIZE);
  fprintf(stderr, "Second chunk: %p %p\n", other_chunk_cursor, other_chunk_end);

  current_objects = new std::vector<int32_t*>();
  other_objects = new std::vector<int32_t*>();
}

void memory_teardown() {
  free(current_chunk);
  free(other_chunk);

  delete current_objects;
  delete other_objects;
}

void do_gc(std::int32_t* stack_low, std::int32_t* stack_high);

// FIXME: stack_high is always the same, no need to pass it more than once.
void* memory_allocate(int32_t size, int32_t* stack_low, int32_t* stack_high) {
  fprintf(stderr, "Allocate %d\n", size);

  int32_t* result = 0;
  int gc_count = 0;
  while (gc_count <= 1) {
    if (current_chunk_cursor + size + 2 < current_chunk_end) {
      fprintf(stderr, "Fits in the current chunk\n");
      // Reserve space for size and color.
      // FIXME: compact; no need to use 8 bytes for them. Also add helpers.
      result = reinterpret_cast<int32_t*>(current_chunk_cursor);
      result += 2;
      fprintf(stderr, "Allocation result: %p\n", result);
      memset(result, 0, size);
      int32_t* p = reinterpret_cast<int32_t*>(current_chunk_cursor);
      *p = size;
      fprintf(stderr, "Object at %p, size at %p, ", result, p);
      ++p;
      fprintf(stderr, "color at %p\n", p);
      *p = COLOR_WHITE;
      current_chunk_cursor += (size + 2 * INT_SIZE);

      current_objects->push_back(result);
      return result;
    }
    fprintf(stderr, "Doesn't fit in the current chunk\n");
    // Doesn't fit. Collect garbage. Then try again.
    do_gc(stack_low, stack_high);
    ++gc_count;
  }

  // Tried GC but the object still doesn't fit. Out of memory.
  fprintf(stderr, "Error: out of memory\n");
  assert(false);
  return nullptr;
}

bool find_object(int32_t* ptr_to_object, int32_t** object, int32_t* offset) {
  // ptr_to_object is a pointer to somewhere inside the object.

  // FIXME: binary search.
  for (size_t i = 0; i < current_objects->size(); ++i) {
    fprintf(stderr, "comparing against current object %p\n", current_objects->at(i)); 
    int32_t* maybe_right_object = current_objects->at(i);
    if (maybe_right_object == ptr_to_object) {
      *offset = 0;
      *object = maybe_right_object;
      return true;
    } else if (maybe_right_object < ptr_to_object && (i == current_objects->size() - 1 || current_objects->at(i + 1) > ptr_to_object)) {
      // Last chance! Check if that object is big enough for our pointer.

      if (maybe_right_object + get_byte_size(maybe_right_object) / INT_SIZE > ptr_to_object) {
        *offset = (ptr_to_object - maybe_right_object) / INT_SIZE;
        *object = maybe_right_object;
        return true;
      }
      return false;
    } else if (maybe_right_object > ptr_to_object) {
      return false;
    }
  }
}

bool move_object(int32_t* ptr_to_object, int32_t** new_ptr, std::stack<std::pair<int32_t**, int32_t*>>* ptrs) {
  fprintf(stderr, "Processing ptr %p\n", ptr_to_object);
  int32_t* object;
  int32_t offset;

  if (!find_object(ptr_to_object, &object, &offset)) {
    fprintf(stderr, "Ptr doesn't belong to an object\n");
    return false;
  }

  // Maybe this object has been moved already?
  int32_t color = get_color(object);
  fprintf(stderr, "Moving object %p\n", object);
  if (color == COLOR_MOVED) {
    int32_t* new_address = reinterpret_cast<int32_t*>(get_byte_size(object));
    *new_ptr = new_address + offset;
    fprintf(stderr, "Already moved\n");
    return true;
  }

  int32_t byte_size = get_byte_size(object);
  fprintf(stderr, "Size in bytes %d\n", byte_size);
  assert(byte_size % INT_SIZE == 0);

  // Copy the raw bytes.
  // FIXME: assert that alignment is ok.
  int32_t* new_address = reinterpret_cast<int32_t*>(other_chunk_cursor);
  memcpy(other_chunk_cursor, object - 2, byte_size + 2 * INT_SIZE);
  other_chunk_cursor += byte_size + 2 * INT_SIZE;

  new_address += 2;
  fprintf(stderr, "new address is %p\n", new_address);
  other_objects->push_back(new_address);

  // Mark the object as moved
  set_color(object, COLOR_MOVED);
  set_byte_size(object, reinterpret_cast<int32_t>(new_address));

  // Go through all the fields. If something looks like an object, mark it as
  // something that has to be moved.
  int32_t* p = new_address;
  for (size_t i = 0; i < byte_size / INT_SIZE; ++i) {
    if (is_in_current_chunk(reinterpret_cast<void*>(*p))) {
      fprintf(stderr, "Discovered pointer %p\n", reinterpret_cast<void*>(*p));
      ptrs->push(std::make_pair(reinterpret_cast<int32_t**>(p), reinterpret_cast<int32_t*>(*p)));
    }
    p++;
  }

  *new_ptr = new_address + offset;
  return true;
}

void mark_and_sweep(std::stack<std::pair<int32_t**, int32_t*>>* ptrs) {
  // Iterate through known objects.
  while (!ptrs->empty()) {
    auto ptr_pair = ptrs->top();
    ptrs->pop();

    int32_t** location = ptr_pair.first;
    int32_t* ptr = ptr_pair.second;

    fprintf(stderr, "Visiting object %p\n", ptr);
    move_object(ptr, location, ptrs);
  }
}

void do_gc(std::int32_t* stack_low, std::int32_t* stack_high) {
  fprintf(stderr, "GC starting\n");
  fprintf(stderr, "Current chunk: %p %p %p\n", current_chunk, current_chunk_cursor, current_chunk_end);
  fprintf(stderr, "%d full, no of objects: %d\n", 100 * (current_chunk_cursor - current_chunk) / (current_chunk_end - current_chunk), current_objects->size());

  // Discover potential pointers. They can be in the stack or in the current
  // memory chunk, pointed to by already discovered pointers.
  int32_t* p;
  std::stack<std::pair<int32_t**, int32_t*>> roots;

  fprintf(stderr, "stack %p %p\n", stack_low, stack_high);

  for (p = stack_low; p < stack_high; ++p) {
    fprintf(stderr, "%p: %p\n", (void*)p, (void*)*p);
    int32_t* maybe_ptr = reinterpret_cast<int32_t*>(*p);
    if (is_in_current_chunk(maybe_ptr)) {
      // FIXME: Is this always a pointer? Do we need to know something more
      // complicated about the structure of the stack?
      fprintf(stderr, "Found pointer %p\n", maybe_ptr);
      roots.push(std::make_pair(reinterpret_cast<int32_t**>(p), maybe_ptr));
    }
  }

  mark_and_sweep(&roots);

  std::swap(current_chunk, other_chunk);
  std::swap(current_chunk_cursor, other_chunk_cursor);
  std::swap(current_chunk_end, other_chunk_end);
  std::swap(current_objects, other_objects);

  zap_memory(other_chunk, CHUNK_SIZE);
  other_chunk_cursor = other_chunk;
  other_objects->clear();

  fprintf(stderr, "GC done\n");
  fprintf(stderr, "Current chunk: %p %p %p\n", current_chunk, current_chunk_cursor, current_chunk_end);
  fprintf(stderr, "%d full, no of objects: %d\n", 100 * (current_chunk_cursor - current_chunk) / (current_chunk_end - current_chunk), current_objects->size());

}

void memory_test_do_gc(int32_t* stack_low, int32_t* stack_high) {
  do_gc(stack_low, stack_high);
}

bool memory_test_is_live_object(int32_t* object) {
  int32_t* found_object;
  int32_t offset;
  if (find_object(object, &found_object, &offset) && offset == 0) {
    assert(found_object == object);
    return true;
  }
  return false;
}
