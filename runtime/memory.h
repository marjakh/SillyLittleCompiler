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
void memory_test_set_gc_stress();
bool memory_test_is_live_object(int32_t* object);

class TemporaryHandle {
 public:
  TemporaryHandle(std::int32_t* ptr);
  ~TemporaryHandle();

  std::int32_t* ptr() const {
    return ptr_;
  }

  std::int32_t** ptr_location() {
    return &ptr_;
  }

 private:
  std::int32_t* ptr_;

  TemporaryHandle(const TemporaryHandle&) = delete;
  void operator=(const TemporaryHandle&) = delete;
};


#endif
