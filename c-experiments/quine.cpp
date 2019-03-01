#include <iostream>
std::string escape(std::string s) {
  std::string r = "";
  for (char c : s) {
    if (c == 92) {
      r += "\\\\";
    } else if (c == 34) {
      r += "\\\"";
    } else if (c == 10) {
      r += "\\n";
    } else {
      r += c;
    }
  }
  return r;
}
void eniuq(std::string s) {
  std::cout << s << "(\"" << escape(s) << "\");\n  return 0;\n}" << std::endl;
}
int main(void) {
  eniuq("#include <iostream>\nstd::string escape(std::string s) {\n  std::string r = \"\";\n  for (char c : s) {\n    if (c == 92) {\n      r += \"\\\\\\\\\";\n    } else if (c == 34) {\n      r += \"\\\\\\\"\";\n    } else if (c == 10) {\n      r += \"\\\\n\";\n    } else {\n      r += c;\n    }\n  }\n  return r;\n}\nvoid eniuq(std::string s) {\n  std::cout << s << \"(\\\"\" << escape(s) << \"\\\");\\n  return 0;\\n}\" << std::endl;\n}\nint main(void) {\n  eniuq");
  return 0;
}
