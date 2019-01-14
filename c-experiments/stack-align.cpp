#include <cstdio>


void foo1() {
}

void foo2(int) {
}


int main(void) {
  // int i = 8;
  // int j = 10;
  // int k = 16;
  // int l = 20;
  // int m = 21;
  foo1();
  foo2(1);
  return 0;
}

// g++ -m32 stack-align.cpp
