#include "stack_walk.h"

#include "function_context.h"
#include "tagging.h"

#include <cassert>
#include <iostream>

const int pushed_register_count = 3;

void stack_walk(std::int32_t* stack_low, std::int32_t* stack_high, std::stack<std::pair<int32_t**, std::int32_t*>>* roots) {
  // std::cerr << "Stack walk " << stack_low << " " << stack_high << std::endl;
  std::int32_t* ebp = stack_low;
  while (ebp <= stack_high) {
    // Verify magic number.
    std::int32_t* p = ebp - 1;
    // std::cerr << "Found frame " << ebp << std::endl;
    int32_t* magic = reinterpret_cast<int32_t*>(*(p--));
    // std::cerr << "Magic number " << magic << std::endl;
    assert(magic == reinterpret_cast<int32_t*>(0xc0decafe));
    FunctionContext* function_context = reinterpret_cast<FunctionContext*>(untag_pointer(reinterpret_cast<int32_t*>(*p)));
    roots->push(std::make_pair(reinterpret_cast<int32_t**>(p), reinterpret_cast<int32_t*>(function_context)));
    --p;
    // std::cerr << "Spill count " << function_context->spill_count << std::endl;
    // std::cerr << "Outer " << function_context->outer << std::endl;
    // std::cerr << "params_and_locals_count " << function_context->params_and_locals_count << std::endl;
    // Iterate spill area.
    for (int i = 0; i < function_context->spill_count; ++i) {
      int32_t* maybe_ptr = reinterpret_cast<int32_t*>(*p);
      // std::cerr << "Spilled: " << maybe_ptr << std::endl;
      if (has_pointer_tag(maybe_ptr)) {
        roots->push(std::make_pair(reinterpret_cast<int32_t**>(p), untag_pointer(maybe_ptr)));
      }
      --p;
    }
    // Iterate pushed registers.
    for (int i = 0; i < pushed_register_count; ++i) {
      int32_t* maybe_ptr = reinterpret_cast<int32_t*>(*p);
      // std::cerr << "Pushed: " << maybe_ptr << std::endl;
      if (has_pointer_tag(maybe_ptr)) {
        roots->push(std::make_pair(reinterpret_cast<int32_t**>(p), untag_pointer(maybe_ptr)));
      }
      --p;
    }
    // Next stack frame.
    if (ebp == stack_high) {
      break;
    }
    assert(*ebp >= reinterpret_cast<int32_t>(ebp));
    ebp = reinterpret_cast<int32_t*>(*ebp);
  }
}
