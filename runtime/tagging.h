#ifndef RUNTIME_TAGGING_H
#define RUNTIME_TAGGING_H

#include "constants.h"

#include <cassert>
#include <cstdint>
#include <cstdio>

template<typename T>
bool has_pointer_tag(T* value) {
  return (reinterpret_cast<int32_t>(value) & INT_PTR_TAG_MASK) == PTR_TAG;
}

inline bool has_pointer_tag(int32_t value) {
  return (value & INT_PTR_TAG_MASK) == PTR_TAG;
}

inline bool has_int_tag(int32_t value) {
  return !has_pointer_tag(value);
}

inline int32_t untag_int(int32_t value) {
  // To be used only in contexts where the value *must* be an int, otherwise
  // it's a code generation error.
  assert(!has_pointer_tag(value));
  return value >> TAG_SHIFT;
}

template<typename T>
int32_t* untag_pointer(T* value) {
  // To be used only in contexts where the value *must* be a pointer, otherwise
  // it's a code generation error.
  assert(has_pointer_tag(value));
  return reinterpret_cast<int32_t*>(reinterpret_cast<int32_t>(value) ^ PTR_TAG);
}

template<typename T>
int32_t* tag_pointer(T* value) {
  assert(!has_pointer_tag(value));
  return reinterpret_cast<int32_t*>(reinterpret_cast<int32_t>(value) | PTR_TAG);
}

#endif
