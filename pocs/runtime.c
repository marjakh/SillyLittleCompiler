#include <stdio.h>

extern void user_code(void);

void RuntimeHello() {
  printf("Hello!\n");
}

void RuntimeWithParam(int i) {
  printf("The param was %d\n", i);
}

int RuntimeReturning() {
  return 25;
}

int main(int argc, char** argv) {
  printf("Runtime starting\n");
  user_code();
  printf("Runtime exiting\n");
  return 0;
}

// Compile & link like this:
// as -32 -ggstabs -o use_runtime.o use_runtime.asm && gcc -m32 -c runtime.c -o runtime.o && gcc -m32 runtime.o use_runtime.o && echo done


