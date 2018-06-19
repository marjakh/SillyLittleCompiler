#!/usr/bin/python3

from constants import *
from grammar import GrammarDriver
from grammar_rules import rules
from parse_tree import *
from parser import Parser
from scanner import Scanner, TokenType
from scope_analyser import ScopeAnalyser, ScopeType, FunctionVariable
from util import print_debug
from variable import Function as variable_Function

from enum import Enum

import sys

output = ""

class RuntimeError(BaseException):
  def __init__(self, message, pos = None):
    self.message = message
    self.pos = pos


class FunctionContext:
  def __init__(self, function):
    self.function = function
    self.__symbols = dict()

  def addVariable(self, variable, value):
    # print_debug("Adding variable into FunctionContext: " + str(variable))
    assert(variable)
    self.__symbols[variable] = value

  def updateVariable(self, variable, value):
    if variable in self.__symbols:
      self.__symbols[variable] = value
    else:
      assert(self.function)
      self.function.outer_function_context.updateVariable(variable, value)

  def variableValue(self, variable):
    if variable in self.__symbols:
      return self.__symbols[variable]
    assert(self.function)
    return self.function.outer_function_context.variableValue(variable)

  def hasVariable(self, variable):
    return variable in self.__symbols


class FunctionType(Enum):
  user_function = 0
  builtin_function = 1


# Function is a run-time thing.
class Function:
  def __init__(self, function_statement, outer_function_context):
    self.function_statement = function_statement
    self.outer_function_context = outer_function_context

  def __str__(self):
    return "Function(" + self.function_statement.name + ")"

  def execute(self, parameters):
    return None


class Array:
  def __init__(self, size):
    self.size = size
    self.values = [None]*size

  def getData(self, index):
    # FIXME: better runtime error for overflow
    return self.values[index]

  def setData(self, index, new_value):
    # FIXME: better runtime error for overflow
    self.values[index] = new_value


class BuiltinFunction:
  def __init__(self, name, code):
    self.name = name
    self.code = code

  def execute(self, parameters):
    return self.code(parameters)


def write_builtin(parameters):
  assert(len(parameters) == 1)
  global output
  if parameters[0] == None:
    output += "undefined"
  else:
    output += str(parameters[0])
  output += "\n"
  return None


def array_builtin(parameters):
  assert(len(parameters) == 1)
  return Array(parameters[0])


class Interpreter:
  def __init__(self, grammar, source):
    self.grammar = grammar
    self.source = source
    # FIXME: reverse the stack; be consistent!
    self.__function_context_stack = [FunctionContext(None)]

  def run(self):
    global output
    output = ""

    scanner = Scanner(self.source)
    p = Parser(scanner, self.grammar)
    p.parse()
    if not p.success:
      raise p.error

    main_variable = FunctionVariable(MAIN_NAME, MAIN_NAME, None, None)
    p.program.main_function = variable_Function(main_variable)
    p.program.main_function.name = MAIN_NAME
    p.program.main_function.unique_name = MAIN_NAME

    sa = ScopeAnalyser(p.program)

    sa.builtins.add("write")
    sa.builtins.add("Array")
    sa.analyse()

    if not sa.success:
      raise sa.error

    # Install builtins to the top scope.
    self.__function_context_stack[0].addVariable(sa.top_scope.resolve("write"), BuiltinFunction("write", write_builtin))
    self.__function_context_stack[0].addVariable(sa.top_scope.resolve("Array"), BuiltinFunction("Array", array_builtin))

    self.__executeStatements(p.program.statements)

    return output

  def __executeStatements(self, statements):
    # We need to execute function declarations first since they're
    # hoisted. Executing them doesn't do anything else than to create the
    # corresponding Function objects.

    for s in statements:
      if isinstance(s, FunctionStatement):
        (did_return, maybe_return_value) = self.__executeStatement(s)
        assert(not did_return)

    for s in statements:
      if isinstance(s, FunctionStatement):
        continue
      # print("Executing " + str(s))
      (did_return, maybe_return_value) = self.__executeStatement(s)
      if did_return:
        # The statement we executed was a return statement; skip the rest of the
        # function.
        # TODO: do something about allowing or disallowing top-level return. Or meh.
        return (True, maybe_return_value)
    return (False, None)

  def __executeStatement(self, s):
    # print("Executing " + str(s))
    if isinstance(s, LetStatement):
      assert(s.resolved_variable)
      # The variable gets created in the current context.
      self.__function_context_stack[0].addVariable(s.resolved_variable, self.__evaluateExpression(s.expression))
      return (False, None)
    if isinstance(s, AssignmentStatement):
      if isinstance(s.where, VariableExpression):
        assert(s.resolvedVariable())

        new_value = self.__evaluateExpression(s.expression)
        # Maybe the variable is in the current function context...
        if s.resolvedVariable().allocation_scope.scope_type == ScopeType.function:
          self.__function_context_stack[0].updateVariable(s.resolvedVariable(), new_value)
        else: # Or in the top scope.
          assert(s.resolvedVariable().allocation_scope.scope_type == ScopeType.top)
          self.__function_context_stack[-1].updateVariable(s.resolvedVariable(), new_value)
      elif isinstance(s.where, ArrayIndexExpression):
        self.__evaluateExpression(s.where.array).setData(self.__evaluateExpression(s.where.index), self.__evaluateExpression(s.expression))
      else:
        assert(False)
      return (False, None)
    if isinstance(s, FunctionCall):
      value = self.__evaluateExpression(s)
      return (False, value)
    if isinstance(s, IfStatement):
      if self.__evaluateExpression(s.expression):
        (did_return, maybe_return_value) = self.__executeStatements(s.then_body)
      else:
        (did_return, maybe_return_value) = self.__executeStatements(s.else_body)
      return (did_return, maybe_return_value)
    if isinstance(s, WhileStatement):
      while self.__evaluateExpression(s.expression):
        (did_return, maybe_return_value) = self.__executeStatements(s.body)
        if did_return:
          return (True, maybe_return_value)
      return (False, None)
    if isinstance(s, ReturnStatement):
      if s.expression:
        value = self.__evaluateExpression(s.expression)
      else:
        value = None
      return (True, value)
    if isinstance(s, FunctionStatement):
      # This code is executed when we see a function (this might be an inner
      # function of a function we're already executing, or a top level
      # function).
      self.__function_context_stack[0].addVariable(s.resolved_function, Function(s, self.__function_context_stack[0]))
      return (False, None)
    assert(False)

  def __evaluateExpression(self, e):
    # print_debug("Evaluating " + str(e))
    if isinstance(e, NumberExpression):
      return e.value
    if isinstance(e, VariableExpression):
      assert(e.resolved_variable)
      # Maybe the variable is in the current function context, or in some outer
      # function context... (note that variableValue() walks the stack!)
      if e.resolved_variable.allocation_scope.scope_type == ScopeType.function:
        return self.__function_context_stack[0].variableValue(e.resolved_variable)
      # Or in the top context.
      assert(e.resolved_variable.allocation_scope.scope_type == ScopeType.top)
      return self.__function_context_stack[-1].variableValue(e.resolved_variable)
    if isinstance(e, AddExpression):
      ix = 1
      current = self.__evaluateExpression(e.items[0])
      assert(len(e.items) % 2 == 1)
      while ix < len(e.items):
        if e.items[ix].token_type == TokenType.plus:
          current += self.__evaluateExpression(e.items[ix + 1])
        elif e.items[ix].token_type == TokenType.minus:
          current -= self.__evaluateExpression(e.items[ix + 1])
        else:
          assert(False)
        ix += 2
      return current
    if isinstance(e, MultiplyExpression):
      ix = 1
      current = self.__evaluateExpression(e.items[0])
      assert(len(e.items) % 2 == 1)
      while ix < len(e.items):
        if e.items[ix].token_type == TokenType.multiplication:
          current *= self.__evaluateExpression(e.items[ix + 1])
        elif e.items[ix].token_type == TokenType.division:
          current //= self.__evaluateExpression(e.items[ix + 1])
        else:
          assert(False)
        ix += 2
      return current
    if isinstance(e, BooleanExpression):
      e1 = self.__evaluateExpression(e.items[0])
      e2 = self.__evaluateExpression(e.items[2])
      if e.items[1].token_type == TokenType.equals:
        return e1 == e2
      if e.items[1].token_type == TokenType.not_equals:
        return e1 != e2
      if e.items[1].token_type == TokenType.less_than:
        return e1 < e2
      if e.items[1].token_type == TokenType.less_or_equals:
        return e1 <= e2
      if e.items[1].token_type == TokenType.greater_than:
        return e1 > e2
      if e.items[1].token_type == TokenType.greater_or_equals:
        return e1 >= e2
    if isinstance(e, FunctionCall):
      # FIXME: arrays impl
      parameters = [self.__evaluateExpression(p) for p in e.parameters]
      assert(e.function.resolvedVariable())
      f = e.function.resolvedVariable()

      # We might have a user-defined function, direct call: function foo() { ... } foo();
      # or a user-defined function, indirect call: function foo() { } let bar = foo; bar();

      # In the former case, the FunctionStatement might be after the call. But
      # that's taken care of separately (by hoisting the FunctionStatements), so
      # we don't need to worry about it here.

      # Maybe the variable is in the current function context, or in some outer
      # function context... (note that variableValue() walks the stack!)
      if f.allocation_scope.scope_type == ScopeType.function:
        value = self.__function_context_stack[0].variableValue(f)
      else:
        # Or in the top context.
        assert(f.allocation_scope.scope_type == ScopeType.top)
        value = self.__function_context_stack[-1].variableValue(f)

      if isinstance(value, BuiltinFunction):
        return value.execute(parameters)

      if not isinstance(value, Function):
        raise RuntimeError("RuntimeError: Calling something which is not a function", e.pos)

      function_statement = value.function_statement

      if len(parameters) != len(function_statement.parameter_names):
        raise RuntimeError("RuntimeError: Wrong number of parameters, expecting " + str(len(function_statement.parameter_names)), e.pos)

      # Create a FunctionContext for the function we're about to call.
      self.__function_context_stack = [FunctionContext(value)] + self.__function_context_stack

      for i in range(len(parameters)):
        self.__function_context_stack[0].addVariable(function_statement.function.parameter_variables[i], parameters[i])
      (did_return, maybe_return_value) = self.__executeStatements(function_statement.body)


      self.__function_context_stack.pop(0)
      return maybe_return_value

    if isinstance(e, NewExpression):
      parameters = [self.__evaluateExpression(p) for p in e.parameters]
      assert(e.function_call.function.resolved_variable)
      f = e.function_call.function.resolved_variable
      value = self.__function_context_stack[-1].variableValue(f)
      if isinstance(value, BuiltinFunction):
        r = value.execute(parameters)
        return r
      # No user defined classes yet.
      assert(False)

    if isinstance(e, ArrayIndexExpression):
      array = self.__evaluateExpression(e.array)
      index = self.__evaluateExpression(e.index)
      return array.getData(index)

    assert(False)


if __name__ == "__main__":
  input_file = open(sys.argv[1], 'r')
  source = input_file.read()
  grammar = GrammarDriver(rules)
  i = Interpreter(grammar, source)
  # try:
  #   output = i.run().strip()
  #   print(output)
  # except BaseException as e:
  #   print("Got error")
  #   print(e)
  #   exit(1)
  output = i.run().strip()
  print(output)
