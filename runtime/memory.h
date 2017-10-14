#ifndef RUNTIME_MEMORY_H
#define RUNTIME_MEMORY_H

#include <cinttypes>

void memory_init();

void memory_teardown();

void* memory_allocate(std::int32_t size, std::int32_t* stack_low, std::int32_t* stack_high);

// For testing purposes
void memory_test_do_gc(std::int32_t* stack_low, std::int32_t* stack_high);
bool memory_test_is_live_object(int32_t* object);

#endif
