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
