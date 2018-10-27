#ifndef RUNTIME_ERRORS_H
#define RUNTIME_ERRORS_H

#include <cstdio>
#include <cstdlib>

inline void terminate_with_runtime_error(const char* error) {
  printf("RuntimeError: %s\n", error);
  exit(0);
}

#endif
