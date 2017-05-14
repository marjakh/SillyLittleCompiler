#!/usr/bin/python3

from util import *
from type_enums import VariableType

# Temp constructs
class AssignmentStatementContinuation:
  def __init__(self, items, pos):
    self.expression = items[0]
    self.pos = pos


class ArrayIndexContinuation:
  def __init__(self, items, pos):
    self.index_expression = items[0]
    assert(items[1] is None or isinstance(items[1], ArrayIndexContinuation))
    self.continuation = items[1]
    self.pos = pos


class ParameterList:
  def __init__(self, items, pos):
    self.parameters = items
    self.pos = pos


class ElseStatementTemp:
  def __init__(self, items, pos):
    self.body = items[0]
    self.pos = pos


# Real parse tree nodes
class ParseTreeNode:
  def __init__(self, pos):
    self.pos = pos

class Statement(ParseTreeNode):
  def __init__(self, pos):
    super().__init__(pos)
    self.scope = None

class FunctionStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.name = items[0].value
    self.parameter_names = items[1] or []
    self.body = items[2] or []
    self.resolved_variable = None
    self.function = None # The Function object created during scope analysis.

  def __str__(self):
    return "FunctionStatement(" + str(self.name) + ", " + listToString(self.parameter_names) + ", " + listToString(self.body) + ")"

  def accept(self, visitor):
    visitor.visitFunctionStatement(self)

class LetStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 2)
    self.identifier = items[0].value
    self.expression = items[1]
    self.resolved_variable = None

  def __str__(self):
    return "LetStatement(" + str(self.identifier) + ", " + str(self.expression) + ")"

  def accept(self, visitor):
    visitor.visitLetStatement(self)


class AssignmentStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 2)
    assert(isinstance(items[0], VariableExpression) or isinstance(items[0], ArrayIndexExpression))
    self.where = items[0]
    self.expression = items[1]

  def __str__(self):
    return "AssignmentStatement(" + str(self.where) + ", " + str(self.expression) + ")"

  def accept(self, visitor):
    visitor.visitAssignmentStatement(self)

  def identifierName(self):
    if isinstance(self.where, VariableExpression):
      return self.where.name
    elif isinstance(self.where, ArrayIndexExpression):
      return self.where.arrayName()
    assert(False)

  def resolvedVariable(self):
    # FIXME: huh?
    if isinstance(self.where, VariableExpression):
      return self.where.resolvedVariable()
    elif isinstance(self.where, ArrayIndexExpression):
      return self.where.resolvedVariable()
    assert(False)


class IfStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 3)
    self.expression = items[0]
    self.then_body = items[1] or []
    if items[2]:
      assert(isinstance(items[2], ElseStatementTemp))
      self.else_body = items[2].body or []
    else:
      self.else_body = []
    self.if_scope = None
    self.else_scope = None

  def __str__(self):
    return "IfStatement(" + str(self.expression) + ", " + listToString(self.then_body) + ", " + listToString(self.else_body) + ")"

  def accept(self, visitor):
    visitor.visitIfStatement(self)


class WhileStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 2)
    self.expression = items[0]
    self.body = items[1] or []
    self.scope = None

  def __str__(self):
    return "WhileStatement(" + str(self.expression) + ", " + listToString(self.body) + ")"

  def accept(self, visitor):
    visitor.visitWhileStatement(self)


class ReturnStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.expression = items[0]

  def __str__(self):
    return "ReturnStatement(" + str(self.expression) + ")"

  def accept(self, visitor):
    visitor.visitReturnStatement(self)


class Expression(ParseTreeNode):
  def __init__(self, pos):
    super().__init__(pos)


class FunctionCall(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(isinstance(items[0], VariableExpression) or isinstance(items[0], ArrayIndexExpression))
    self.function = items[0]
    if items[1] is None:
      self.parameters = []
    else:
      self.parameters = items[1]

  def __str__(self):
    return "FunctionCall(" + str(self.function) + ", " + listToString(self.parameters) + ")"

  def accept(self, visitor):
    visitor.visitFunctionCall(self)

  def is_direct(self):
    return self.function.resolvedVariable().variable_type == VariableType.user_function or self.function.resolvedVariable().variable_type == VariableType.builtin_function


class VariableExpression(Expression):
  def __init__(self, name, pos):
    super().__init__(pos)
    self.name = name
    self.resolved_variable = None

  def __str__(self):
    return "VariableExpression(" + str(self.name) + ")"

  def accept(self, visitor):
    visitor.visitVariableExpression(self)

  def resolvedVariable(self):
    return self.resolved_variable


class ArrayIndexExpression(Expression):
  def __init__(self, array, index, pos):
    super().__init__(pos)
    assert(isinstance(array, VariableExpression) or isinstance(array, ArrayIndexExpression))
    assert(isinstance(index, Expression))
    self.array = array
    self.index = index

  def __str__(self):
    return "ArrayIndexExpression(" + str(self.array) + ", " + str(self.index) + ")"

  def accept(self, visitor):
    visitor.visitArrayIndexExpression(self)

  def resolvedVariable(self):
    # FIXME: it can also be a function return value: f()[3]. Make this more
    # generic.
    if isinstance(self.array, VariableExpression):
      return self.array.resolved_variable
    elif isinstance(self.array, ArrayIndexExpression):
      return self.array.resolvedVariable()
    assert(False)

  def arrayName(self):
    if isinstance(self.array, VariableExpression):
      return self.array.name
    elif isinstance(self.array, ArrayIndexExpression):
      return self.array.arrayName()
    assert(False)


class NumberExpression(Expression):
  def __init__(self, value, pos):
    super().__init__(pos)
    self.value = value

  def __str__(self):
    return "NumberExpression(" + str(self.value) + ")"

  def accept(self, visitor):
    visitor.visitNumberExpression(self)


class NewExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.class_name = items[0].value
    self.parameters = items[1] or []

  def accept(self, visitor):
    visitor.visitNewExpression(self)


class AddExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.items = items

  def __str__(self):
    return "AddExpression(" + listToString(self.items) + ")"

  def accept(self, visitor):
    visitor.visitAddExpression(self)


class MultiplyExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.items = items

  def __str__(self):
    return "MultiplyExpression(" + listToString(self.items) + ")"

  def accept(self, visitor):
    visitor.visitMultiplyExpression(self)


class BooleanExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 3)
    self.items = items

  def __str__(self):
    return "BooleanExpression(" + listToString(self.items) + ")"

  def accept(self, visitor):
    visitor.visitBooleanExpression(self)


class Program(ParseTreeNode):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.statements = items[0] or []

  def __str__(self):
    return "Program(" + listToString(self.statements) + ")"


class ParseTreeVisitor:
  def __init__(self):
    self.visit_expressions = True

  def visitProgram(self, program):
    for s in program.statements:
      s.accept(self)

  def visitLetStatement(self, statement):
    if self.visit_expressions:
      statement.expression.accept(self)

  def visitAssignmentStatement(self, statement):
    if self.visit_expressions:
      statement.expression.accept(self)

  def visitIfStatement(self, statement):
    if self.visit_expressions:
      statement.expression.accept(self)
    self.visitIfStatementBeginBody(statement)
    for s in statement.then_body:
      s.accept(self)
    self.visitIfStatementEndBody(statement)
    self.visitIfStatementBeginElse(statement)
    for s in statement.else_body:
      s.accept(self)
    self.visitIfStatementEndElse(statement)

  def visitIfStatementBeginBody(self, statement):
    pass

  def visitIfStatementEndBody(self, statement):
    pass

  def visitIfStatementBeginElse(self, statement):
    pass

  def visitIfStatementEndElse(self, statement):
    pass

  def visitWhileStatement(self, statement):
    if self.visit_expressions:
      statement.expression.accept(self)
    self.visitWhileStatementBeginBody(statement)
    for s in statement.body:
      s.accept(self)
    self.visitWhileStatementEndBody(statement)

  def visitWhileStatementBeginBody(self, statement):
    pass

  def visitWhileStatementEndBody(self, statement):
    pass

  def visitFunctionStatement(self, statement):
    self.visitFunctionStatementBeginBody(statement)
    self.visitFunctionStatementParameters(statement)
    for s in statement.body:
      s.accept(self)
    self.visitFunctionStatementEndBody(statement)

  def visitFunctionStatementBeginBody(self, statement):
    pass

  def visitFunctionStatementParameters(self, parameters):
    pass

  def visitFunctionStatementEndBody(self, statement):
    pass

  def visitFunctionCall(self, statement):
    if self.visit_expressions:
      for e in statement.parameters:
        e.accept(self)

  def visitReturnStatement(self, statement):
    if self.visit_expressions:
      if statement.expression:
        statement.expression.accept(self)

  def visitVariableExpression(self, expression):
    assert(self.visit_expressions)
    pass

  def visitArrayIndexExpression(self, expression):
    assert(self.visit_expressions)
    pass

  def visitNumberExpression(self, expression):
    assert(self.visit_expressions)
    pass

  def visitAddExpression(self, expression):
    assert(self.visit_expressions)
    for i in expression.items:
      if isinstance(i, ParseTreeNode):
        i.accept(self)

  def visitMultiplyExpression(self, expression):
    assert(self.visit_expressions)
    for i in expression.items:
      if isinstance(i, ParseTreeNode):
        i.accept(self)

  def visitBooleanExpression(self, expression):
    assert(self.visit_expressions)
    for i in expression.items:
      if isinstance(i, ParseTreeNode):
        i.accept(self)

  def visitNewExpression(self, expression):
    assert(self.visit_expressions)
    for e in expression.parameters:
      e.accept(self)
