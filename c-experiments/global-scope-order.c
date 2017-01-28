/* Mutually recursive functions must use forward declarations.
*/

#include <stdio.h>

int first = 10;

void bar();

void foo() {
  fprintf(stderr, "first is %d\n", first);
  /* A function cannot use a variable declared later! */
  /* fprintf(stderr, "second is %d\n", second); */
  ++first;
  /* However, it's not a problem to call a function that uses "second" here,
   * because this is not JavaScript. By the time main is called, the global
   * scope is already initialized.*/
  if (first < 12) bar();
}

int second = 10;

void bar() {
  fprintf(stderr, "first is %d\n", first);
  fprintf(stderr, "second is %d\n", second);
  ++second;
  if (second < 12) foo();
}

int main(int argc, char** argv) {
  foo();
  return 0;
}
