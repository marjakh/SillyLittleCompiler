#ifndef RUNTIME_MEMORY_H
#define RUNTIME_MEMORY_H

void memory_init(void* stack);

void memory_teardown();

void* memory_allocate(int size, void* stack_when_entering_runtime);

#endif
