#!/usr/bin/python3

from grammar import GrammarDriver, SyntaxError
from grammar_rules import rules
from parse_tree import *
from scanner import Scanner, TokenType

class Parser:
  def __init__(self, scanner, grammar):
    self.__scanner = scanner
    self.__grammar = grammar
    self.__stack = ["program"]
    self.__ctor_stack = []
    self.program = None

  def parse(self):
    pos = self.__scanner.pos
    token = self.__scanner.nextToken()
    # print("Got token " + str(token))

    while len(self.__stack):
      # print("Stack is " + str(self.__stack))
      # print("Token is " + str(token))
      # print("Ctor stack is " + list_to_string(self.__ctor_stack))

      while self.__stack[0] == "epsilon":
        self.__gather(None, pos)
        self.__stack.pop(0)

      # print("Stack is " + str(self.__stack))
      # print("Token is " + str(token))
      # print("Ctor stack is " + list_to_string(self.__ctor_stack))

      if self.__stack[0] == token.name():
        self.__stack.pop(0)
        # print("Consumed " + str(token))
        self.__gather(token, pos)
        pos = self.__scanner.pos
        token = self.__scanner.nextToken()
        # print("Got token " + str(token))
        continue

      try:
        (prediction, rule) = self.__grammar.predict(self.__stack[0], token.name())
        self.success = True
      except SyntaxError as e:
        self.success = False
        self.error = e
        e.pos = pos
        e.message = ("Syntax error: Expected " + str(self.__stack[0]) + ", got " +
                     str(token.name()) + ".")
        return

      if rule and rule.gatherer:
        # print("rule is " + str(rule.gatherer))
        self.__ctor_stack = [rule.gatherer()] + self.__ctor_stack

      # print("Got prediction " + str(prediction))
      self.__stack = prediction + self.__stack[1:]

  def __gather(self, item, pos):
    #print("gather " + str(self.__ctor_stack))
    #print("gather " + str(item))
    if len(self.__ctor_stack) == 0:
      #print("no more ctor stack");
      #print(str(item))
      return
    if self.__ctor_stack[0]:
      self.__ctor_stack[0].add(item, pos)
      while self.__ctor_stack[0].done():
        result = self.__ctor_stack[0].result()
        self.__ctor_stack.pop(0)
        if len(self.__ctor_stack) == 0:
          # We're done with the program. Save it.
          self.program = result
          return
        # FIXME: pos here might be wrong; not sure.
        # print("re-routing result " + str(result))
        self.__ctor_stack[0].add(result, pos)

if __name__ == "__main__":
  grammar = GrammarDriver(rules)

  test_progs = [
    # Valid programs
    ("foo = 1;", True),
    ("foo = bar;", True),
    ("foo = 1 + 2;", True),
    ("foo = 1 + 2 + 3;", True),
    ("foo = 1; bar = 2;", True),
    ("foo = 1 - 2 * 3;", True),
    ("foo = (1 - 2) * 3;", True),
    ("foo = 1 / 2 - 3 * 4;", True),
    ("foo = bar / baz - quux * other;", True),
    ("foo = 3 * 4;", True),
    ("read(foo);", True),
    ("write(3 + 4);", True),
    ("if (bar == baz) { }", True),
    ("if (bar == baz) { foo = 1; }", True),
    ("if (3 + 4 / foo == 5 * 8) { foo = 1; }", True),
    ("if (bar == baz) { } else { }", True),
    ("if (bar == baz) { foo = 1; } else { foo = 2; }", True),
    ("if (bar == baz) { foo = 1; bar = baz; } else { foo = 2; baz = bar;}", True),
    ("bar = 3; if (bar == baz) { } baz = 4;", True),
    ("while (bar == baz) { }", True),
    ("while (bar == baz) { foo = foo + 1; }", True),
    ("let i = 0; while (i < 10) { i = i + 1; }", True),
    ("let v1 = 0; if (v1 == 0) { let v2 = 0; } let v3 = 0;", True),
    ("foo();", True),
    ("foo(bar);", True),
    ("foo(bar, bar2);", True),
    ("let baz = foo();", True),
    ("let baz = foo(bar);", True),
    ("let baz = foo(bar, bar2);", True),
    ("if (foo() == 0) { }", True),
    ("if (foo(bar) == 0) { }", True),
    ("if (foo(bar, bar2) == 0) { }", True),
    ("i[0] = 0;", True),
    ("i[0][0] = j[0];", True),
    ("i = j[0]();", True),
    ("if (i[0] == j[0]) { }", True),
    ("let i = new Foo();", True),
    ("let i = new Foo(1);", True),
    ("let i = new Foo(1, 2);", True),
    ("if (new Foo() == 0) { }", True),
    ("if (new Foo(1) == 0) { }", True),
    ("if (new Foo(1, 2) == 0) { }", True),
    ("bar(new Foo());", True),
    ("bar(new Foo(1));", True),
    ("bar(new Foo(1, 2));", True),
    # Errorneous programs
    ("foo 1 2 write();", False),
    ("write(1 2 3;", False),
    ("1 2 3;", False),
    ("foo = ) + 1", False),
    ("1 )", False),
    ("foo 1", False),
    ("foo;", False),
    ("foo = bar == baz;", False),
    ("write(bar == baz);", False),
  ]

  for (source, expected_success) in test_progs:
    print("Test:")
    print(source)
    scanner = Scanner(source)
    p = Parser(scanner, grammar)
    p.parse()
    if p.success:
      print(str(p.program))
    else:
      print("-" * p.error.pos, end="")
      print("*")
      print(p.error.message)
    assert(expected_success == p.success);
  print("All OK!")


