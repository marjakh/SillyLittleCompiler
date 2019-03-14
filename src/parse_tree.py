#!/usr/bin/python3

from util import *
from scanner import Token
from type_enums import VariableType

# Temp constructs
class AssignmentStatementContinuation:
  def __init__(self, items, pos):
    self.expression = items[0]
    self.pos = pos


class ArrayIndexContinuation:
  def __init__(self, items, pos):
    self.index_expression = items[0]
    assert(items[1] is None or isinstance(items[1], ArrayIndexContinuation) or isinstance(items[1], FunctionCallContinuation))
    self.continuation = items[1]
    self.pos = pos


class FunctionCallContinuation:
  def __init__(self, items, pos):
    self.call_expression = items[0]
    assert(items[1] is None or isinstance(items[1], ArrayIndexContinuation) or isinstance(items[1], FunctionCallContinuation))
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


class ElseIfStatementTemp:
  def __init__(self, items, pos):
    self.condition = items[0]
    self.body = items[1] or []
    self.continuation = items[2]
    self.pos = pos


# Real parse tree nodes
class ParseTreeNode:
  def __init__(self, pos):
    self.pos = pos

class Statement(ParseTreeNode):
  def __init__(self, pos):
    super().__init__(pos)
    self.scope = None


class FormalParameter(ParseTreeNode):
  def __init__(self, name, ttype, pos):
    super().__init__(pos)
    self.name = name.value
    if ttype is None:
      self.ttype = "any"
    else:
      self.ttype = ttype.value


class FormalParameterList(ParseTreeNode):
  def __init__(self, items, pos):
    super().__init__(pos)
    if items is None:
      self.items = []
    else:
      assert(len(items) == 3)
      self.items = [FormalParameter(items[0], items[1], pos)]
      if items[2] is not None:
        assert(isinstance(items[2], FormalParameterListContinuation))
        self.items.extend(items[2].items)

  def __str__(self):
    s = "["
    for p in self.items:
      if s != "[":
        s += ", "
      s += p.name + ": " + p.ttype
    s += "]"
    return s


class FormalParameterListContinuation(ParseTreeNode):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 3)
    self.items = [FormalParameter(items[0], items[1], pos)]
    if items[2] is not None:
      assert(isinstance(items[2], FormalParameterListContinuation))
      self.items.extend(items[2].items)


class FunctionStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.name = items[0].value
    self.formal_parameters = items[1] or FormalParameterList(None, pos)
    if items[2] is not None:
      assert(isinstance(items[2], Token))
      self.return_type = items[2].value
    else:
      self.return_type = "any"
    self.body = items[3] or []
    self.resolved_variable = None
    self.function = None # The Function object created during scope analysis.

  def __str__(self):
    return "FunctionStatement(" + str(self.name) + ", " + str(self.return_type) + ", " + str(self.formal_parameters) + ", " + list_to_string(self.body) + ")"

  def accept(self, visitor):
    visitor.visitFunctionStatement(self)

class LetStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 3)
    self.identifier = items[0].value
    if items[1] is not None:
      assert(isinstance(items[1], Token))
      self.ttype = items[1].value
    else:
      self.ttype = "any"
    self.expression = items[2]
    self.resolved_variable = None

  def __str__(self):
    return "LetStatement(" + str(self.identifier) + ", " + str(self.ttype) + ", " + str(self.expression) + ")"

  def accept(self, visitor):
    visitor.visitLetStatement(self)


class AssignmentStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 2)
    assert(isinstance(items[0], VariableExpression) or isinstance(items[0], ArrayIndexExpression) or isinstance(items[0], FunctionCall))
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
    elif isinstance(self.where, FunctionCall):
      return self.where.function.name()
    assert(False)


class IfStatement(Statement):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 3)
    self.expression = items[0]
    self.then_body = items[1] or []
    if items[2]:
      if isinstance(items[2], ElseStatementTemp):
        self.else_body = items[2].body or []
      elif isinstance(items[2], ElseIfStatementTemp):
        self.else_body = [IfStatement([items[2].condition, items[2].body, items[2].continuation], items[2].pos)]
      else:
        assert(False)

    else:
      self.else_body = []
    self.if_scope = None
    self.else_scope = None

  def __str__(self):
    return "IfStatement(" + str(self.expression) + ", " + list_to_string(self.then_body) + ", " + list_to_string(self.else_body) + ")"

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
    return "WhileStatement(" + str(self.expression) + ", " + list_to_string(self.body) + ")"

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
  def __init__(self, function, parameters, pos):
    super().__init__(pos)
    assert(isinstance(function, VariableExpression) or isinstance(function, ArrayIndexExpression) or isinstance(function, FunctionCall))
    self.function = function
    self.parameters = parameters or []

  def __str__(self):
    return "FunctionCall(" + str(self.function) + ", " + list_to_string(self.parameters) + ")"

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
    assert(isinstance(array, VariableExpression) or isinstance(array, ArrayIndexExpression) or isinstance(array, FunctionCall))
    assert(isinstance(index, Expression))
    self.array = array
    self.index = index

  def __str__(self):
    return "ArrayIndexExpression(" + str(self.array) + ", " + str(self.index) + ")"

  def accept(self, visitor):
    visitor.visitArrayIndexExpression(self)

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


class StringExpression(Expression):
  def __init__(self, value, pos):
    super().__init__(pos)
    self.value = value

  def __str__(self):
    return "StringExpression(" + str(self.value) + ")"

  def accept(self, visitor):
    visitor.visitStringExpression(self)


class NewExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.class_name = items[0].value
    self.parameters = items[1] or []
    self.function_call = FunctionCall(VariableExpression(self.class_name, pos), self.parameters, pos)

  def accept(self, visitor):
    visitor.visitNewExpression(self)


class AddExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.items = items

  def __str__(self):
    return "AddExpression(" + list_to_string(self.items) + ")"

  def accept(self, visitor):
    visitor.visitAddExpression(self)


class MultiplyExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.items = items

  def __str__(self):
    return "MultiplyExpression(" + list_to_string(self.items) + ")"

  def accept(self, visitor):
    visitor.visitMultiplyExpression(self)


class BooleanExpression(Expression):
  def __init__(self, items, pos):
    super().__init__(pos)
    assert(len(items) == 3)
    self.items = items

  def __str__(self):
    return "BooleanExpression(" + list_to_string(self.items) + ")"

  def accept(self, visitor):
    visitor.visitBooleanExpression(self)


class Program(ParseTreeNode):
  def __init__(self, items, pos):
    super().__init__(pos)
    self.statements = items[0] or []

  def __str__(self):
    return "Program(" + list_to_string(self.statements) + ")"


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

  def visitStringExpression(self, expression):
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
