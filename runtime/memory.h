#ifndef RUNTIME_MEMORY_H
#define RUNTIME_MEMORY_H

void memory_init();

void memory_teardown();

void* memory_allocate(int size, int* stack_low, int* stack_high);

#endif
