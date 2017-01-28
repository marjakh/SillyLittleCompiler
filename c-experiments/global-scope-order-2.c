/* Mutually recursive functions must use forward declarations.
*/

#include <stdio.h>

int bar();

int foo() { return bar(); }
/* This doesn't work, since the initializer is not a constant!
int x = foo();
*/
int x = 0;
int bar() { return x; }

int main(int argc, char** argv) {
  fprintf(stderr, "x is %d\n", x);
  return 0;
}
