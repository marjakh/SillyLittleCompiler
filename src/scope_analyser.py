#!/usr/bin/python3

from grammar import GrammarDriver
from grammar_rules import rules
from parse_tree import ParseTreeVisitor, VariableExpression, ArrayIndexExpression
from parser import Parser
from scanner import Scanner
from type_enums import VariableType, ScopeType
from variable import Variable, FunctionVariable, Function
from util import print_debug

from enum import Enum

class ScopeError(BaseException):
  def __init__(self, message, pos = None):
    self.message = message
    self.pos = pos


class Scope:
  def __init__(self, scope_type, parent=None):
    self.scope_type = scope_type
    self.parent = parent
    # [Variable]. The variables are gathered as a list, because we want to keep
    # them in order (for simplicity; we also want to always allocate the
    # variables in the same order to be deterministic).
    self.variables = []
    self.children = []

  def __getVariable(self, name):
    for v in self.variables:
      if v.name == name:
        return v
    return None

  def addVariable(self, variable):
    # print("Adding variable " + str(variable) + " to scope " + str(self))
    if self.__getVariable(variable.name):
      return False
    # Allow shadowing; here we explicitly don't care if some parent declares the
    # same variable. So, a variable in an if scope can shadow a variable in a
    # function.
    self.variables.append(variable)
    return True

  def resolve(self, name):
    # print("Resolving variable " + str(name) + " in scope " + str(self))
    v = self.__getVariable(name)
    if v:
      return v
    # print("Not found, going to parent...")
    if self.parent:
      return self.parent.resolve(name)
    return None


# Base class for a parse tree visitor which knows about scopes. It either
# creates them if the scopes don't exist, or keeps track of already created
# scopes while walking.
class ScopeAnalyserVisitor(ParseTreeVisitor):
  def __init__(self, top_scope):
    super().__init__()
    self.scopes = [top_scope]

  def visitIfStatementBeginBody(self, statement):
    # Here we'd really like to use a pointer to the member variable, so that
    # __pushScope could assign the scope it creates into the right place.
    self.__pushScope(statement.if_scope, ScopeType.sub)
    statement.if_scope = self.scopes[0]

  def visitIfStatementEndBody(self, statement):
    self.__popScope()

  def visitIfStatementBeginElse(self, statement):
    self.__pushScope(statement.else_scope, ScopeType.sub)
    statement.else_scope = self.scopes[0]

  def visitIfStatementEndElse(self, statement):
    self.__popScope()

  def visitWhileStatementBeginBody(self, statement):
    self.__pushScope(statement.scope, ScopeType.sub)
    statement.scope = self.scopes[0]

  def visitWhileStatementEndBody(self, statement):
    self.__popScope()

  def visitFunctionStatementBeginBody(self, statement):
    self.__pushScope(statement.function.scope, ScopeType.function)
    statement.function.scope = self.scopes[0]

  def visitFunctionStatementEndBody(self, statement):
    self.__popScope()

  def currentScopeType(self):
    # Are we inside a function scope or on the top scope?
    for scope in self.scopes:
      if scope.scope_type is not ScopeType.sub:
        return scope.scope_type
    assert(False)

  def currentVariableAllocationScope(self):
    # Returns the innermost scope which is either function or top (not
    # sub). That's the scope where the variables will be allocated.
    for scope in self.scopes:
      if scope.scope_type is not ScopeType.sub:
        return scope
    assert(False)

  def currentFunctionScope(self):
    # Returns the innermost scope which is either function or top (not
    # sub). That's the scope where the variables will be allocated.
    for scope in self.scopes:
      if scope.scope_type == ScopeType.function:
        return scope
    return None

  def __pushScope(self, scope, scope_type):
    if scope is None:
      scope = Scope(scope_type, self.scopes[0])
    self.scopes[0].children += [scope] # FIXME: reverse the stack, this is silly
    self.scopes = [scope] + self.scopes

  def __popScope(self):
    self.scopes.pop(0)



# Creates scopes and puts functions into them.
class FirstPassScopeAnalyser(ScopeAnalyserVisitor):
  def __init__(self, top_scope):
    super().__init__(top_scope)
    self.__function_stack = []

  def visitFunctionStatement(self, s):
    # Add the function variable into the surrounding scope.
    # print("Adding function variable " + s.name + " into scope " + str(self.scopes[0]))
    v = FunctionVariable(s.name, self.currentVariableAllocationScope(), s)
    if not self.scopes[0].addVariable(v):
      raise ScopeError("ScopeError: redeclaration of variable " + s.name, s.pos)
    s.resolved_function = v
    f = Function(v)
    if self.__function_stack:
      f.outer_function = self.__function_stack[-1]
      f.name = f.outer_function.name + "%" + s.name
    else:
      f.name = s.name
    self.__function_stack.append(f)
    s.function = f

    # This will create the scope for the function.
    super().visitFunctionStatement(s)
    self.__function_stack.pop()



# Uses the scopes created by FirstPassScopeAnalyser, puts variables into them
# and resolves variables (incl. function calls).
class SecondPassScopeAnalyser(ScopeAnalyserVisitor):
  def __init__(self, top_scope):
    super().__init__(top_scope)

  @staticmethod
  def __addVariablesFromScopeChainToFunction(function, scope):
    for v in scope.variables:
      function.addVariable(v)
    for s in scope.children:
      SecondPassScopeAnalyser.__addVariablesFromScopeChainToFunction(function, s)

  def visitLetStatement(self, s):
    super().visitLetStatement(s)
    v = Variable(s.identifier, VariableType.variable, self.currentVariableAllocationScope())
    # print("Adding normal variable " + s.identifier + " into scope " + str(self.scopes[0]))
    if not self.scopes[0].addVariable(v):
      raise ScopeError("ScopeError: redeclaration of variable " + s.identifier, s.pos)
    s.resolved_variable = v

  def visitAssignmentStatement(self, s):
    super().visitAssignmentStatement(s)

    self.__visitVariableExpressionOrArrayIndexExpression(s.where)

  def __visitVariableExpressionOrArrayIndexExpression(self, e):
    if isinstance(e, VariableExpression):
      self.visitVariableExpression(e)
    elif isinstance(e, ArrayIndexExpression):
      self.visitArrayIndexExpression(e)
    else:
      assert(False)

  def visitVariableExpression(self, e):
    v = self.scopes[0].resolve(e.name)
    if not v:
      raise ScopeError("ScopeError: undeclared variable " + e.name, e.pos)
    e.resolved_variable = v
    if v.allocation_scope.scope_type == ScopeType.function and v.allocation_scope != self.currentFunctionScope():
      v.referred_by_inner_functions = True

  def visitArrayIndexExpression(self, e):
    self.__visitVariableExpressionOrArrayIndexExpression(e.array)
    e.index.accept(self)

  def visitFunctionStatementEndBody(self, s):
    super().visitFunctionStatementEndBody(s)

    # Gather all local variables for the function (they might be directly in the
    # function scope or in subscopes (for while, if etc.).

    # For simplicity, we treat all variables the same, that is, allocate all
    # variables in the function context. A possible optimization is to stack
    # allocate variables which are not referred to by the inner functions.

    # FIXME: optimize so that variables which are not live at the same time can
    # share the space.
    SecondPassScopeAnalyser.__addVariablesFromScopeChainToFunction(s.function, s.function.scope)

  def visitFunctionCall(self, s):
    super().visitFunctionCall(s)

    self.__visitVariableExpressionOrArrayIndexExpression(s.function)

    # We cannot check parameter count here, because we might be calling a
    # function via a variable!

  def visitFunctionStatementParameters(self, s):
    # TODO: parameters need to keep track of which functions they are a parameter to.
    super().visitFunctionStatementParameters(s)
    for p in s.parameter_names: # p is Token
      assert(s.function.scope)
      v = Variable(p.value, VariableType.variable, s.function.scope, True)
      # Note that parameter can also be referred to by inner functions.
      if not self.scopes[0].addVariable(v):
        raise ScopeError("ScopeError: redeclaration of variable " + p.value, s.pos)

class ScopeAnalyser:
  def __init__(self, parse_tree):
    self.__parse_tree = parse_tree
    self.builtins = set()

  def analyse(self):
    self.top_scope = Scope(ScopeType.top)

    for b in self.builtins:
      self.top_scope.addVariable(Variable(b, VariableType.builtin_function, self.top_scope))

    v1 = FirstPassScopeAnalyser(self.top_scope)
    v2 = SecondPassScopeAnalyser(self.top_scope)
    try:
      v1.visitProgram(self.__parse_tree)
      v2.visitProgram(self.__parse_tree)
      self.success = True
    except ScopeError as e:
      self.success = False
      self.error = e


if __name__ == "__main__":
  grammar = GrammarDriver(rules)

  test_progs = [
    # Valid programs
    ("let foo = 1; foo = 2;", True),
    ("let v1 = 0; if (v1 == 0) { let v2 = 0; } let v3 = 0;", True),
    ("let foo = 0; let bar = foo;", True),
    ("let foo = 0; foo = read(); write(foo);", True),
    ("let foo = 0; let indirect = write; indirect(foo);", True),
    ("write(id(1));", True),
    ("function foo() { } write(foo());", True),
    ("let foo = 1; foo[0] = 3;", True),
    ("let foo = 1; foo[0][0] = 3;", True),
    ("let foo = 1; foo[0]();", True),
    ("let foo = 1; write(foo[0]);", True),
    ("let foo = 1; write(foo[0][0]);", True),
    ("let foo = 1; write(foo[0]());", True),
    ("let foo = 1; let bar = 2; foo[bar] = 3;", True),
    ("let foo = 1; let bar = 2; foo[bar][0] = 3;", True),
    ("let foo = 1; let bar = 2; foo[0][bar] = 3;", True),
    ("let foo = 1; let bar = 2; write(foo[bar]);", True),
    ("let foo = 1; let bar = 2; write(foo[bar][0]);", True),
    ("let foo = 1; let bar = 2; write(foo[0][bar]);", True),
    ("let foo = 1; let bar = 2; write(foo[bar]());", True),
    # Errorneous programs
    ("let foo = 1; let foo = 2;", False),
    ("let foo = foo;", False),
    ("let foo = bar;", False),
    ("if (bar == 0) { }", False),
    ("let foo = 0; bar(foo);", False),
    ("let foo = id(foo);", False),
    ("sth[0] = 3;", False),
    ("sth[0][0] = 3;", False),
    ("sth[0][0]();", False),
    ("let foo = 1; foo[bar] = 3;", False),
    ("let foo = 1; foo[bar][0] = 3;", False),
    ("let foo = 1; foo[0][bar] = 3;", False),
    ("let foo = 1; write(foo[bar]);", False),
    ("let foo = 1; write(foo[bar][0]);", False),
    ("let foo = 1; write(foo[0][bar]);", False),
    ("let foo = 1; write(foo[bar]());", False),
  ]

  for (source, expected_success) in test_progs:
    print("Test:")
    print(source)
    scanner = Scanner(source)
    p = Parser(scanner, grammar)
    p.parse()
    assert(p.success)
    sa = ScopeAnalyser(p.program)
    sa.builtins.add("read")
    sa.builtins.add("write")
    sa.builtins.add("id")
    sa.analyse()
    if sa.success:
      pass
    else:
      print("-" * sa.error.pos, end="")
      print("*")
      print(sa.error.message)
    assert(sa.success == expected_success)
  print("All OK!")

