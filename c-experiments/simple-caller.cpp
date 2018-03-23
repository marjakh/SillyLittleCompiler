// g++ -m32 simple-caller.cpp

int foo(int a, int b, int c) {
  return a + b + c;
}


int main(int argc, char** argv) {
  foo(1, 2, 3);
  return 0;
}
