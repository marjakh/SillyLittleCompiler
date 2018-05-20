#ifndef RUNTIME_MEMORY_H
#define RUNTIME_MEMORY_H

#include <cstdint>

void memory_init();
void memory_teardown();

void memory_set_stack_high(std::int32_t* stack_high);

void* memory_allocate(std::int32_t size, std::int32_t* stack_low);
void* memory_allocate_no_gc(std::int32_t size);

// For testing purposes
void memory_test_do_gc(std::int32_t* stack_low);
bool memory_test_is_live_object(int32_t* object);

#endif
