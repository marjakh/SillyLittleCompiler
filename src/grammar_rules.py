#!/usr/bin/python3

# This file defines the actual grammar rules for our language.

from grammar import GrammarDriver, GrammarRule, SyntaxError
from parse_tree import *
from util import *

class Gatherer:
  def __init__(self, name, mask, ctor):
    self.__name = name
    self.__ix = 0
    self.__mask = mask
    self.__gathered = []
    self.__ctor = ctor
    self.__pos = None

  def add(self, item, pos):
    if self.__mask[self.__ix]:
      self.__gathered.append(item)
    self.__ix += 1
    if self.__pos is None:
      self.__pos = pos

  def done(self):
    return self.__ix == len(self.__mask)

  def result(self):
    return self.__ctor(self.__gathered, self.__pos)

  def __str__(self):
    return self.__name


just_route = lambda: Gatherer("JustRoute", [True], lambda items, pos: items[0])
flatten = lambda n: lambda: Gatherer("Flatten", [True] * n, flatten_items)

def add_expr_from_items(items, pos):
  if items[1]:
    return AddExpression(flatten_items(items), pos)
  return items[0]

def mul_expr_from_items(items, pos):
  if items[1]:
    return MultiplyExpression(flatten_items(items), pos)
  return items[0]

def flatten_items(items, pos = None):
  new_items = []
  for i in items:
    if isinstance(i, list):
      new_items += i
    elif i:
      new_items += [i]
  return new_items

def dispatch_assignment_continuation(items, pos):
  assert(len(items) == 2)
  if isinstance(items[1], AssignmentStatementContinuation):
    return AssignmentStatement([items[0], items[1].expression], pos)
  assert(items[1] is None)
  return items[0]

def dispatch_array_index_or_function_call(items, pos):
  assert(len(items) == 2)

  def to_expression(item, pos):
    if isinstance(item, ArrayIndexExpression) or isinstance(item, FunctionCall):
      return item
    return VariableExpression(item.value, pos)

  if items[1] is None:
    return to_expression(items[0], pos)

  if isinstance(items[1], ArrayIndexContinuation):
    return dispatch_array_index_or_function_call([ArrayIndexExpression(to_expression(items[0], pos), items[1].index_expression, pos), items[1].continuation], pos)
  elif isinstance(items[1], FunctionCallContinuation):
    return dispatch_array_index_or_function_call([FunctionCall(to_expression(items[0], pos), items[1].call_expression, pos), items[1].continuation], pos)
  else:
    assert(False)


rules = [
    GrammarRule("program", ["statement_list", "token_eos"],
                lambda: Gatherer("ProgramGatherer",
                                 [True, False], lambda items, pos: Program(items, pos))),
    GrammarRule("statement_list", ["epsilon"], None),
    GrammarRule("statement_list", ["statement", "statement_list"], flatten(2)),

    GrammarRule("statement",
                ["identifier_or_array_or_function_call", "assignment_continuation"],
                lambda: Gatherer("AssignmentStatement",
                                 [True, True], dispatch_assignment_continuation)),
    GrammarRule("assignment_continuation",
                ["token_assign", "expression", "token_semicolon"],
                lambda: Gatherer("AssignmentStatementContinuationGatherer",
                                 [False, True, False],
                                 lambda items, pos: AssignmentStatementContinuation(items, pos))),

    GrammarRule("assignment_continuation", ["token_semicolon"], lambda: Gatherer("None", [False], lambda items, pos: None)),

    GrammarRule("statement",
                ["token_keyword_let", "token_identifier", "token_assign", "expression", "token_semicolon"],
                lambda: Gatherer("LetStatementGatherer",
                                 [False, True, False, True, False],
                                 lambda items, pos: LetStatement(items, pos))),

    GrammarRule("statement",
                ["token_keyword_function", "token_identifier", "token_left_paren", "parameter_name_list", "token_right_paren", "token_left_curly", "statement_list", "token_right_curly"],
                lambda: Gatherer("FunctionStatementGatherer",
                                 [False, True, False, True, False, False, True, False],
                                 lambda items, pos: FunctionStatement(items, pos))),

    GrammarRule("statement",
                ["token_keyword_return", "expression_or_none", "token_semicolon"],
                lambda: Gatherer("ReturnStatementGatherer",
                                 [False, True, False],
                                 lambda items, pos: ReturnStatement(items, pos))),

    GrammarRule("expression_or_none", ["epsilon"], None),
    GrammarRule("expression_or_none", ["expression"], just_route),

    GrammarRule("parameter_name_list", ["epsilon"], None),
    GrammarRule("parameter_name_list",
                ["token_identifier", "parameter_name_list_continuation"], flatten(2)),
    GrammarRule("parameter_name_list_continuation", ["epsilon"], None),
    GrammarRule("parameter_name_list_continuation",
                ["token_comma", "token_identifier", "parameter_name_list_continuation"],
                lambda: Gatherer("ParameterNameListContinuationGatherer", [False, True, True],
                                 lambda items, pos: flatten_items(items))),

    GrammarRule("statement",
                ["token_keyword_if", "token_left_paren", "bool_expression", "token_right_paren",
                 "token_left_curly", "statement_list", "token_right_curly", "maybe_else_if"],
                lambda: Gatherer("IfStatementGatherer",
                                 [False, False, True, False, False, True, False, True],
                                 lambda items, pos: IfStatement(items, pos))),
    GrammarRule("maybe_else_if", ["token_keyword_else", "maybe_else_if_continuation"], lambda: Gatherer("ElseStatementGatherer", [False, True], lambda items, pos: items[0])),
    GrammarRule("maybe_else_if", ["epsilon"], None),

    GrammarRule("maybe_else_if_continuation",
                ["token_keyword_if", "token_left_paren", "bool_expression", "token_right_paren", "token_left_curly", "statement_list", "token_right_curly", "maybe_else_if"],
                lambda: Gatherer("ElseIfStatementTempGatherer",
                                 [False, False, True, False, False, True, False, True],
                                 lambda items, pos: ElseIfStatementTemp(items, pos))),
    GrammarRule("maybe_else_if_continuation",
                ["token_left_curly", "statement_list", "token_right_curly"],
                lambda: Gatherer("ElseStatementTempGatherer",
                                 [False, True, False],
                                 lambda items, pos: ElseStatementTemp(items, pos))),
    GrammarRule("statement",
                ["token_keyword_while", "token_left_paren", "bool_expression", "token_right_paren",
                 "token_left_curly", "statement_list", "token_right_curly"],
                lambda: Gatherer("IfStatementGatherer",
                                 [False, False, True, False, False, True, False],
                                 lambda items, pos: WhileStatement(items, pos))),
    GrammarRule("bool_expression", ["expression", "bool_op", "expression"],
                lambda: Gatherer("BooleanExpressionGatherer",
                                 [True, True, True],
                                 lambda items, pos: BooleanExpression(items, pos))),
    GrammarRule("expression", ["token_keyword_new", "token_identifier", "token_left_paren", "parameter_list", "token_right_paren"],
                lambda: Gatherer("NewExpressionGatherer",
                                 [False, True, False, True, False],
                                 lambda items, pos: NewExpression(items, pos))),
    GrammarRule("expression", ["add_term", "add_term_tail"],
                lambda: Gatherer("ExpressionGatherer",
                                 [True, True], add_expr_from_items)),

    GrammarRule("add_term_tail", ["epsilon"], None),
    GrammarRule("add_term_tail", ["add_op", "add_term", "add_term_tail"], flatten(3)),
    GrammarRule("add_term", ["mul_term", "mul_term_tail"],
                lambda: Gatherer("AddTermGatherer", [True, True], mul_expr_from_items)),
    GrammarRule("mul_term_tail", ["epsilon"], None),
    GrammarRule("mul_term_tail", ["mul_op", "mul_term", "mul_term_tail"], flatten(3)),
    GrammarRule("mul_term", ["token_number"],
                lambda: Gatherer("NumberExpression", [True],
                                 lambda items, pos: NumberExpression(items[0].value, pos))),
    GrammarRule("mul_term", ["token_string"],
                lambda: Gatherer("StringExpression", [True],
                                 lambda items, pos: StringExpression(items[0].value, pos))),
    GrammarRule("mul_term", ["identifier_or_array_or_function_call"], just_route),

    GrammarRule("parameter_list", ["epsilon"], None),
    GrammarRule("parameter_list", ["expression", "parameter_list_continuation"], flatten(2)),
    GrammarRule("parameter_list_continuation", ["epsilon"], None),
    GrammarRule("parameter_list_continuation", ["token_comma", "expression", "parameter_list_continuation"],
                lambda: Gatherer("ParameterListContinuationGatherer", [False, True, True], lambda items, pos: flatten_items(items))),

    GrammarRule("mul_term", ["token_left_paren", "expression", "token_right_paren"],
                lambda: Gatherer("JustRoute", [False, True, False],
                                 lambda items, pos: items[0])),
    GrammarRule("add_op", ["token_plus"], just_route),
    GrammarRule("add_op", ["token_minus"], just_route),
    GrammarRule("mul_op", ["token_multiplication"], just_route),
    GrammarRule("mul_op", ["token_division"], just_route),
    GrammarRule("bool_op", ["token_equals"], just_route),
    GrammarRule("bool_op", ["token_not_equals"], just_route),
    GrammarRule("bool_op", ["token_less_than"], just_route),
    GrammarRule("bool_op", ["token_less_or_equals"], just_route),
    GrammarRule("bool_op", ["token_greater_than"], just_route),
    GrammarRule("bool_op", ["token_greater_or_equals"], just_route),

    GrammarRule("identifier_or_array_or_function_call", ["token_identifier", "array_or_function_call_continuation"], lambda: Gatherer("ArrayIndexOrFunctionCall", [True, True], dispatch_array_index_or_function_call)),
    GrammarRule("array_or_function_call_continuation", ["epsilon"], None),
    GrammarRule("array_or_function_call_continuation", ["token_left_bracket", "expression", "token_right_bracket", "array_or_function_call_continuation"], lambda: Gatherer("ArrayIndex", [False, True, False, True], lambda items, pos: ArrayIndexContinuation(items, pos))),
    GrammarRule("array_or_function_call_continuation", ["token_left_paren", "parameter_list", "token_right_paren", "array_or_function_call_continuation"], lambda: Gatherer("FunctionCall", [False, True, False, True], lambda items, pos: FunctionCallContinuation(items, pos))),
]
