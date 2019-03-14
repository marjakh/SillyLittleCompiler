#!/usr/bin/python3

from grammar_rules import rules
from scanner import Scanner
from util import list_to_string

from math import floor
from random import random

class Fuzzer:
  def __init__(self, rules):
    self.__rules = rules
    self.__stack = ["program"]

  def run(self):
    program = []
    while len(self.__stack):
      print("Stack: " + list_to_string(self.__stack))
      want = self.__stack.pop(0)
      print("Want " + want)
      if want == "token_eos" or want == "epsilon":
        continue
      if want.startswith("token_keyword"):
        program.append(want[len("token_keyword_"):])
        continue
      if want == "token_identifier":
        # FIXME: choose from applicable identifiers
        program.append("a")
        continue
      if want == "token_number":
        program.append("0")
        continue
      if want.startswith("token_"):
        program.append(Scanner.tokenNameToString(want))
        continue

      applicable_rules = [r for r in rules if r.left == want]
      # In order to not grow the stack, give the simplest production a lot of weight...
      if random() > 0.7:
        ix = 0
      else:
        ix = floor(random() * len(applicable_rules))
      print(list_to_string(applicable_rules))
      print(ix)
      print("Rule: " + str(applicable_rules[ix]))
      self.__stack = applicable_rules[ix].right + self.__stack
      print("Program so far: ")
      print(list_to_string(program, "", "", " "))
    return program

if __name__ == "__main__":
  f = Fuzzer(rules)
  program = f.run()
  print("Program:")
  print(list_to_string(program, "", "", " "))
