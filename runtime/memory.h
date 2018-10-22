#ifndef RUNTIME_MEMORY_H
#define RUNTIME_MEMORY_H

#include "tagging.h"

#include <cstdint>

void memory_init();
void memory_teardown();

void memory_set_stack_high(std::int32_t* stack_high);

std::int32_t* memory_allocate(std::int32_t size, std::int32_t* stack_low);
std::int32_t* memory_allocate_no_gc(std::int32_t size);

// For testing purposes
void memory_test_do_gc(std::int32_t* stack_low);
void memory_test_set_gc_stress();
bool memory_test_is_live_object(int32_t* object);

class TemporaryHandle {
 public:
  TemporaryHandle(std::int32_t* tagged_ptr);
  ~TemporaryHandle();

  std::int32_t* tagged_ptr() const {
    return tagged_ptr_;
  }

  std::int32_t* untagged_ptr() const {
    return untag_pointer(tagged_ptr_);
  }

  std::int32_t** ptr_location() {
    return &tagged_ptr_;
  }

 private:
  std::int32_t* tagged_ptr_;

  TemporaryHandle(const TemporaryHandle&) = delete;
  void operator=(const TemporaryHandle&) = delete;
};


#endif
