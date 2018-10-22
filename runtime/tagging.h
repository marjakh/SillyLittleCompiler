#ifndef RUNTIME_TAGGING_H
#define RUNTIME_TAGGING_H

#include "constants.h"

#include <cassert>
#include <cstdint>
#include <stdio.h>

inline int32_t untag_int(int32_t value) {
  // FIXME: assert that the value has an int tag, throw error otherwise.
  return value >> TAG_SHIFT;
}

template<typename T>
int32_t* untag_pointer(T* value) {
  // FIXME: assert that the value has an int tag, throw error otherwise.
  return reinterpret_cast<int32_t*>(reinterpret_cast<int32_t>(value) ^ PTR_TAG);
}

template<typename T>
bool has_pointer_tag(T* value) {
  return (reinterpret_cast<int32_t>(value) & PTR_TAG_MASK) == PTR_TAG;
}

template<typename T>
int32_t* tag_pointer(T* value) {
  assert(!has_pointer_tag(value));
  return reinterpret_cast<int32_t*>(reinterpret_cast<int32_t>(value) | PTR_TAG);
}

#endif
