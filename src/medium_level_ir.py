#!/usr/bin/python3

from builtin_functions import addBuiltinFunctionShapes
from cfg_creator import BasicBlock, BasicBlockBranch
from parse_tree import *
from scanner import TokenType
from type_enums import ScopeType, VariableType
from variable import Variable, Function
from util import *

"""

Medium-level IR consists of basic blocks, and instructions therein.

Loading:
register = constant
register = local
register = global

Storing:
local = register
global = register

Arithmetic:
register += register
register += constant
The same for -= *= /=

if register < constant goto
if register < register goto
The same for > <= >= == !=

goto

label

call
(Return value must be immediately assigned.)

"""


# TODO: returning function contexts, assigning functions into a variable,
# calling functions via variables...


# FIXME: get rid of labels which are not jump targets.

# TODO: the should be done at scope analysis time, and taking into account that
# variables which are not simultaneously live can share a slot!
def computeVariableOffsetsForFunction(f):
  offset = 0
  for v in f.parameter_variables:
    v.offset = offset
    # FIXME: magic. Which part should know the pointer size anyway?
    offset += 4
  for v in f.local_variables:
    v.offset = offset
    offset += 4

  # FIXME: how do f.local_variables relate to f.scope.variables?
  max_offset = offset
  for s in f.scope.children:
    if s.scope_type == ScopeType.function:
      continue
    assert(s.scope_type == ScopeType.sub)
    new_offset = computeVariableOffsetsForNonFunctionScope(s, offset)
    if new_offset > max_offset:
      max_offset = new_offset
  return max_offset

  return offset

def computeVariableOffsetsForNonFunctionScope(scope, offset=0):
  for v in scope.variables:
    if v.variable_type == VariableType.variable:
      v.offset = offset
      offset += 4
  max_offset = offset
  for s in scope.children:
    if s.scope_type == ScopeType.function:
      continue
    assert(s.scope_type == ScopeType.sub)
    new_offset = computeVariableOffsetsForNonFunctionScope(s, offset)
    if new_offset > max_offset:
      max_offset = new_offset
  return max_offset


class TemporaryVariable(Variable):
  def __init__(self, name):
    super().__init__(name, VariableType.temporary, None)


class Comment:
  def __init__(self, text):
    self.text = text

  def __str__(self):
    return "# " + self.text


class MediumLevelIRInstruction:
  def __init__(self):
    pass


class Label(MediumLevelIRInstruction):
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return self.name + ":"


class Goto(MediumLevelIRInstruction):
  def __init__(self, label):
    super().__init__()
    self.label = label

  def __str__(self):
    return "goto " + self.label


class TestWithOperator(MediumLevelIRInstruction):
  def __init__(self, left, right, op, true_label, false_label):
    super().__init__()
    self.left = left
    self.right = right
    self.op = op
    self.true_label = true_label
    self.false_label = false_label

  def __str__(self):
    return "test " + self.left.name + " " + self.op + " " + self.right.name + "? " + self.true_label + " : " + self.false_label


class TestEquals(TestWithOperator):
  def __init__(self, left, right, true_label, false_label):
    super().__init__(left, right, "==", true_label, false_label)


class TestNotEquals(TestWithOperator):
  def __init__(self, left, right, true_label, false_label):
    super().__init__(left, right, "!=", true_label, false_label)


class TestLessThan(TestWithOperator):
  def __init__(self, left, right, true_label, false_label):
    super().__init__(left, right, "<", true_label, false_label)


class TestLessOrEquals(TestWithOperator):
  def __init__(self, left, right, true_label, false_label):
    super().__init__(left, right, "<=", true_label, false_label)


class TestGreaterThan(TestWithOperator):
  def __init__(self, left, right, true_label, false_label):
    super().__init__(left, right, ">", true_label, false_label)


class TestGreaterOrEquals(TestWithOperator):
  def __init__(self, left, right, true_label, false_label):
    super().__init__(left, right, ">=", true_label, false_label)


class StoreOrLoadTarget:
  def __init__(self):
    pass


class StoreOrLoadTargetWithVariable(StoreOrLoadTarget):
  def __init__(self, variable, depth, is_param, comment):
    self.variable = variable
    assert(depth >= -1) # -1 = global
    self.depth = depth
    self.comment = comment

  def __str__(self):
    return str(self.variable.name)


class Local(StoreOrLoadTargetWithVariable):
  def __init__(self, variable, depth, is_param):
    assert(depth == 0)
    assert(is_param == False)
    super().__init__(variable, 0, False, "local")


class Parameter(StoreOrLoadTargetWithVariable):
  def __init__(self, variable, depth, is_param):
    assert(depth == 0)
    assert(is_param)
    super().__init__(variable, 0, True, "parameter")


class Global(StoreOrLoadTargetWithVariable):
  def __init__(self, variable, depth, is_param):
    assert(depth == -1)
    assert(is_param == False)
    super().__init__(variable, -1, False, "global")


class OuterFunctionLocal(StoreOrLoadTargetWithVariable):
  def __init__(self, variable, depth, is_param):
    assert(depth > 0)
    assert(is_param == False)
    super().__init__(variable, depth, False, "outer function local")


class OuterFunctionParameter(StoreOrLoadTargetWithVariable):
  def __init__(self, variable, depth):
    assert(depth > 0)
    assert(is_param)
    super().__init__(variable, depth, True, "outer function parameter")


class Array(StoreOrLoadTarget):
  def __init__(self, base, index):
    assert(isinstance(base, StoreOrLoadTarget))
    assert(isinstance(index, Constant) or isinstance(index, TemporaryVariable))
    self.base = base
    self.index = index
    self.comment = base.comment + " array"

  def __str__(self):
    return str(self.base) + "[" + self.index.name + "]"


store_or_load_targets = dict()
store_or_load_targets["local"] = dict()
store_or_load_targets["local"]["not_parameter"] = Local
store_or_load_targets["local"]["parameter"] = Parameter
store_or_load_targets["outer"] = dict()
store_or_load_targets["outer"]["not_parameter"] = OuterFunctionLocal
store_or_load_targets["outer"]["parameter"] = OuterFunctionParameter
store_or_load_targets["global"] = dict()
store_or_load_targets["global"]["not_parameter"] = Global


class Constant:
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return str(self.value)


class Load(MediumLevelIRInstruction):
  def __init__(self, what, where):
    assert(isinstance(where, TemporaryVariable))
    self.where = where
    # From: temporary, local variable, global variable, parameter, outer
    # function local, outer function parameter
    assert(isinstance(what, StoreOrLoadTarget))
    self.what = what

  def __str__(self):
    return self.where.name + " = " + str(self.what) + " # " + self.what.comment


class Store(MediumLevelIRInstruction):
  def __init__(self, what, where):
    # To: temporary, local variable, global variable, parameter, outer function
    # local, outer function parameter
    assert(isinstance(where, StoreOrLoadTarget) or isinstance(where, TemporaryVariable))
    self.where = where
    assert(isinstance(what, Constant) or isinstance(what, TemporaryVariable))
    self.what = what

  def __str__(self):
    if isinstance(self.what, Constant):
      what = str(self.what)
    else:
      assert(isinstance(self.what, TemporaryVariable))
      what = self.what.name

    if isinstance(self.where, StoreOrLoadTarget):
      return str(self.where) + " = " + what + " # " + self.where.comment
    else:
      assert(isinstance(self.where, TemporaryVariable))
      return self.where.name + " = " + what


class ArithmeticOperation(MediumLevelIRInstruction):
  def __init__(self, to_variable, from_variable1, from_variable2, operator_string):
    super().__init__()
    self.to_variable = to_variable
    self.from_variable1 = from_variable1
    self.from_variable2 = from_variable2
    self.operator_string = operator_string

  def __str__(self):
    return self.to_variable.name + " = " + self.from_variable1.name + " " + self.operator_string + " " + self.from_variable2.name


class AddTemporaryToTemporary(ArithmeticOperation):
  def __init__(self, to_variable, from_variable1, from_variable2):
    super().__init__(to_variable, from_variable1, from_variable2, "+")


class SubtractTemporaryFromTemporary(ArithmeticOperation):
  def __init__(self, to_variable, from_variable1, from_variable2):
    super().__init__(to_variable, from_variable1, from_variable2, "-")


class MultiplyTemporaryByTemporary(ArithmeticOperation):
  def __init__(self, to_variable, from_variable1, from_variable2):
    super().__init__(to_variable, from_variable1, from_variable2, "*")


class DivideTemporaryByTemporary(ArithmeticOperation):
  def __init__(self, to_variable, from_variable1, from_variable2):
    super().__init__(to_variable, from_variable1, from_variable2, "/")


arithmetic_functions = dict()
arithmetic_functions[TokenType.plus] = AddTemporaryToTemporary
arithmetic_functions[TokenType.minus] = SubtractTemporaryFromTemporary
arithmetic_functions[TokenType.multiplication] = MultiplyTemporaryByTemporary
arithmetic_functions[TokenType.division] = DivideTemporaryByTemporary


class ComparisonBetweenTemporaries(MediumLevelIRInstruction):
  def __init__(self, result_temporary, left_temporary, right_temporary, operator_string):
    super().__init__()
    self.result_temporary = result_temporary
    self.left_temporary = left_temporary
    self.right_temporary = right_temporary
    self.operator_string = operator_string

  def __str__(self):
    return self.result_temporary.name + " = " + self.left_temporary.name + " " + self.operator_string + " " + self.right_temporary.name


# TODO: Add TemporaryEqualsConstant etc.
class TemporaryEqualsTemporary(ComparisonBetweenTemporaries):
  def __init__(self, result_temporary, left_temporary, right_temporary):
    super().__init__(result_temporary,
    left_temporary, right_temporary, "==")


class TemporaryNotEqualsTemporary(ComparisonBetweenTemporaries):
  def __init__(self, result_temporary, left_temporary, right_temporary):
    super().__init__(result_temporary,
    left_temporary, right_temporary, "!=")


class TemporaryLessThanTemporary(ComparisonBetweenTemporaries):
  def __init__(self, result_temporary, left_temporary, right_temporary):
    super().__init__(result_temporary,
    left_temporary, right_temporary, "<")


class TemporaryLessrOrEqualsTemporary(ComparisonBetweenTemporaries):
  def __init__(self, result_temporary, left_temporary, right_temporary):
    super().__init__(result_temporary,
    left_temporary, right_temporary, "<=")


class TemporaryGreaterThanTemporary(ComparisonBetweenTemporaries):
  def __init__(self, result_temporary, left_temporary, right_temporary):
    super().__init__(result_temporary,
    left_temporary, right_temporary, ">")


class TemporaryGreaterOrEqualsTemporary(ComparisonBetweenTemporaries):
  def __init__(self, result_temporary, left_temporary, right_temporary):
    super().__init__(result_temporary,
    left_temporary, right_temporary, ">=")

comparison_functions = dict()
comparison_functions[TokenType.equals] = TemporaryEqualsTemporary
comparison_functions[TokenType.not_equals] = TemporaryNotEqualsTemporary
comparison_functions[TokenType.less_than] = TemporaryLessThanTemporary
comparison_functions[TokenType.less_or_equals] = TemporaryLessrOrEqualsTemporary
comparison_functions[TokenType.greater_than] = TemporaryGreaterThanTemporary
comparison_functions[TokenType.greater_or_equals] = TemporaryGreaterOrEqualsTemporary

test_functions = dict()
test_functions[TokenType.equals] = TestEquals
test_functions[TokenType.not_equals] = TestNotEquals
test_functions[TokenType.less_than] = TestLessThan
test_functions[TokenType.less_or_equals] = TestLessOrEquals
test_functions[TokenType.greater_than] = TestGreaterThan
test_functions[TokenType.greater_or_equals] = TestGreaterOrEquals


class CreateFunctionContext(MediumLevelIRInstruction):
  def __init__(self, temporary_variable, function, call_string):
    super().__init__()
    self.temporary_variable = temporary_variable
    assert(function)
    self.function = function
    self.call_string = call_string

  def __str__(self):
    return self.temporary_variable.name + " = %" + self.call_string + "(" + self.function.name + ")"


class CreateFunctionContextForFunction(CreateFunctionContext):
  def __init__(self, temporary_variable, function):
    super().__init__(temporary_variable, function, "CreateFunctionContextForFunction")


# Create a function context for a function stored in a variable. Note that we
# cannot know (until at run-time) which function there is.
class CreateFunctionContextFromVariable(CreateFunctionContext):
  def __init__(self, temporary_variable, variable_name):
    super().__init__(temporary_variable, variable_name, "CreateFunctionContextFromVariable")
# TODO: how does this work actually? How do we create a function context? Does
# the compiler generate data structures so that we know for each inner function
# how its function context looks like (especially, the number of parameters),
# and then...

# FIXME: assigning functions into variables is unimplemented. We need to create a Function object... and then it must be possible to create a FunctionContext based on it. And the Function object must point to the code. Should the compiler generate them?

class AddParameterToFunctionContext(MediumLevelIRInstruction):
  def __init__(self, temporary_for_function_context, index, temporary_variable):
    super().__init__()
    self.temporary_for_function_context = temporary_for_function_context
    self.index = index
    self.temporary_variable = temporary_variable

  def __str__(self):
    return "%AddParameterToFunctionContext(" + self.temporary_for_function_context.name + ", " + str(self.index) + ", " + self.temporary_variable.name + ")"


class CallFunction(MediumLevelIRInstruction):
  def __init__(self, function, temporary_for_function_context):
    super().__init__()
    self.function = function
    self.temporary_for_function_context = temporary_for_function_context

  def __str__(self):
    return "%CallFunction(" + self.function.name + ", " + self.temporary_for_function_context.name + ")"


class Return(MediumLevelIRInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    return "return"


class GetReturnValue(MediumLevelIRInstruction):
  def __init__(self, temporary_variable, temporary_for_function_context):
    super().__init__()
    self.temporary_variable = temporary_variable
    self.temporary_for_function_context = temporary_for_function_context

  def __str__(self):
    return self.temporary_variable.name + " = %GetReturnValue(" + self.temporary_for_function_context.name + ")"


class SetReturnValueFromTemporary(MediumLevelIRInstruction):
  def __init__(self, temporary_variable):
    super().__init__()
    self.temporary_variable = temporary_variable

  def __str__(self):
    return "%SetReturnValueFromTemporary(" + self.temporary_variable.name + ")"


class SetReturnValueFromConstant(MediumLevelIRInstruction):
  def __init__(self, value):
    super().__init__()
    self.value = value

  def __str__(self):
    return "%SetReturnValueFromConstant(" + str(self.value) + ")"

class MediumLevelIR:
  def __init__(self, blocks, metadata):
    self.blocks = blocks
    self.metadata = metadata


class MediumLevelIRMetadata:
  def __init__(self):
    self.function_param_counts = dict()
    self.function_local_counts = dict()


class MediumLevelIRBasicBlock:
  def __init__(self, id, next_ids, code):
    self.id = id
    self.next_ids = next_ids
    self.code = code


class MediumLevelIRCreator:
  def __init__(self):
    self.__current_function = None
    self.__temporary_count = 0

  def create(self, cfgs, top_scope):
    output = []
    metadata = MediumLevelIRMetadata()

    # First assign offets to variables.
    for [f, cfg] in cfgs:
      assert(f)
      if f.name == "%main":
        metadata.function_local_counts[f.name] = computeVariableOffsetsForNonFunctionScope(top_scope)
        metadata.function_param_counts[f.name] = 0
      else:
        metadata.function_local_counts[f.name] = computeVariableOffsetsForFunction(f)
        # FIXME: params
        metadata.function_param_counts[f.name] = 0

    addBuiltinFunctionShapes(metadata.function_param_counts, metadata.function_local_counts)

    # For each function, create the medium level IR.
    is_first = True
    for [f, cfg] in cfgs:
      self.__current_function = f
      for b in cfg:
        code = self.__createForBasicBlock(b)
        if is_first:
          is_first = False
          code = [Comment("function " + f.name), Label(f.label())] + code
        next_possible = []
        if isinstance(b.next, BasicBlockBranch):
          next_possible = [b.next.true_block.id, b.next.false_block.id]
        elif isinstance(b.next, BasicBlock):
          next_possible = [b.next.id]
        output.append(MediumLevelIRBasicBlock(b.id, next_possible, code))

    # print_debug("Medium-level IR:")
    # for b in output:
    #   print_debug(listToString(b.code, "", "", "\n"))

    return MediumLevelIR(output, metadata)

  def __nextTemporary(self):
    self.__temporary_count += 1
    return TemporaryVariable("%temp" + str(self.__temporary_count - 1))

  def __createForBasicBlock(self, block):
    output = []
    output.append(Label("block_" + str(block.id)))
    for statement in block.statements:
      output.extend(self.__createForStatement(statement))

    if isinstance(block.next, BasicBlock):
      output.append(Goto("block_" + str(block.next.id)))
    elif block.next:
      # FIXME: early return of evaluation for cases like foo() && bar() and foo() || bar().
      # TODO: shortcut if always true / always false (already one level up!)
      assert(isinstance(block.next, BasicBlockBranch))
      condition = block.next.condition
      assert(isinstance(condition, BooleanExpression))

      [temporary1, code1] = self.__computeIntoTemporary(condition.items[0])
      [temporary2, code2] = self.__computeIntoTemporary(condition.items[2])
      output.extend(code1)
      output.extend(code2)
      func = test_functions[condition.items[1].token_type]
      output.append(func(temporary1, temporary2, "block_" + str(block.next.true_block.id), "block_" + str(block.next.false_block.id)))

    else:
      # Block doesn't have a next block, so it just returns (if it's inside a function)
      if len(output) > 0 and not isinstance(output[-1], Return):
        output.append(Return())

    return output

  def __createForStatement(self, statement):
    # print("createForStatement")
    # print(statement)
    if isinstance(statement, LetStatement):
      # We already know about functions and their local variables, so we only
      # care about the assignment part.
      s = AssignmentStatement([VariableExpression(statement.identifier, statement.pos), statement.expression], statement.pos)
      s.where.resolved_variable = statement.resolved_variable
      return self.__createForAssignmentStatement(s)
    if isinstance(statement, AssignmentStatement):
      return self.__createForAssignmentStatement(statement)

    # TODO: optimization: if there are repated calls to a function, we can reuse
    # the function context, we just need to nullify relevant fields.
    if isinstance(statement, FunctionCall):
      temporary_for_function_context = self.__nextTemporary()
      # FIXME: arrays impl
      if statement.is_direct():
        code = [CreateFunctionContextForFunction(temporary_for_function_context, statement.function.resolved_variable)]
      else:
        code = [CreateFunctionContextFromVariable(temporary_for_function_context, statement.function.resolved_variable)]
      for i in range(len(statement.parameters)):
        # TODO: optimization: if the parameter is trivial, we don't need to store it into a temporary
        [temporary, temporary_code] = self.__computeIntoTemporary(statement.parameters[i])
        code += temporary_code + [AddParameterToFunctionContext(temporary_for_function_context, i, temporary)]
      code += [CallFunction(statement.function.resolved_variable, temporary_for_function_context)]
      return code
    if isinstance(statement, ReturnStatement):
      code = []
      if statement.expression:
        if isinstance(statement.expression, NumberExpression):
          code.append(SetReturnValueFromConstant(statement.expression.value))
        else:
          [temporary, code] = self.__computeIntoTemporary(statement.expression)
          code.append(SetReturnValueFromTemporary(temporary))
      code.append(Return())
      return code
    print_error("Unable to create medium level IR for statement:")
    print_error(statement)
    assert(False)
    return []

  def __createForAssignmentStatement(self, statement):
    # TODO: optimization: a = a; should be noop.
    # TODO: optimization: a = 1 + 2; should be precomputed. Note: overflows.

    """
    local = ...
    global = ...
    parameter = ...
    function_context_var = ...
    array[index] = ...
    """

    # FIXME: there shouldn't be a resolvedVariable in the statement (but there
    # is - fix that!).. maybe there should be one in statement.where.

    [where, code] = self.__createStoreOrLoadTarget(statement.where)

    if isinstance(statement.expression, NumberExpression):
      what = Constant(statement.expression.value)
    else:
      # Complex expressions. Compute the expression into a temporary and then
      # store that temporary.
      [temporary, temporary_code] = self.__computeIntoTemporary(statement.expression)
      what = temporary
      code += temporary_code

    code += [Store(what, where)]
    return code

  def __createStoreOrLoadTarget(self, thing):
    if isinstance(thing, ArrayIndexExpression):
      [base, base_code] = self.__createStoreOrLoadTarget(thing.array)
      # FIXME: shortcut constant indices
      [temporary_for_index, code] = self.__computeIntoTemporary(thing.index)
      return [Array(base, temporary_for_index), base_code + code]

    assert(isinstance(thing, VariableExpression))
    variable = thing.resolved_variable

    assert(variable)
    # FIXME: loading functions should be fine too?
    assert(variable.variable_type == VariableType.variable)

    if variable.allocation_scope == self.__current_function.scope:
      scope = "local"
      depth = 0
    elif variable.allocation_scope.scope_type == ScopeType.top:
      scope = "global"
      depth = -1
    else:
      scope = "outer"
      depth = 1
      outer = self.__current_function.outer_function
      assert(outer)
      while variable.allocation_scope != outer.scope:
        depth += 1
        outer = outer.outer_function
        assert(outer)

    if variable.is_parameter:
      is_parameter = "parameter"
    else:
      is_parameter = "not_parameter"
    return [store_or_load_targets[scope][is_parameter](variable, depth, variable.is_parameter), []]

  def __computeIntoTemporary(self, expression):
    if isinstance(expression, NumberExpression):
      # TODO: optimization: many of these can be shortcut.
      temporary = self.__nextTemporary()
      return [temporary, [Store(Constant(expression.value), temporary)]]

    if isinstance(expression, FunctionCall):
      # FIXME: isn't this just dead code? And GetReturnValue too!
      temporary_for_function_context = self.__nextTemporary()
      if expression.is_direct():
        code = [CreateFunctionContextForFunction(temporary_for_function_context, expression.function.resolved_variable)]
      else:
        code = [CreateFunctionContextFromVariable(temporary_for_function_context, expression.function.resolved_variable)]
      for i in range(len(expression.parameters)):
        # TODO: optimization: if the parameter is trivial, we don't need to store it into a temporary
        [temporary, temporary_code] = self.__computeIntoTemporary(expression.parameters[i])
        code += temporary_code + [AddParameterToFunctionContext(temporary_for_function_context, i, temporary)]
      temporary_for_return_value = self.__nextTemporary()
      code += [CallFunction(expression.function.resolved_variable, temporary_for_function_context),
               GetReturnValue(temporary_for_return_value, temporary_for_function_context)]
      return [temporary_for_return_value, code]

    if isinstance(expression, VariableExpression):
      temporary = self.__nextTemporary()
      [what, code] = self.__createStoreOrLoadTarget(expression)
      return [temporary, code + [Load(what, temporary)]]

    if isinstance(expression, ArrayIndexExpression):
      temporary = self.__nextTemporary()
      [what, code] = self.__createStoreOrLoadTarget(expression)
      return [temporary, code + [Load(what, temporary)]]

    if isinstance(expression, AddExpression) or isinstance(expression, MultiplyExpression):
      return self.__accumulateAddExpressionOrMultiplyExpression(expression)

    if isinstance(expression, NewExpression):
      return self.__computeIntoTemporary(expression.function_call)

    print_error("Unable to create pseudo assembly for expression:")
    print_error(expression)
    assert(False)
    return ["not implemented", []]

  def __computeComparisonIntoTemporary(self, temporary1, temporary2, operator):
    temporary = self.__nextTemporary()
    code = [comparison_functions[operator.token_type](temporary, temporary1, temporary2)]
    return [temporary, code]


  def __accumulateAddExpressionOrMultiplyExpression(self, expression):
    # E.g.,
    # a + b + c
    # turns into:
    # t1 = a
    # t2 = b
    # t3 = t1 + t2
    # t4 = c
    # t5 = t3 + t4
    i = 0
    prev_temporary = None
    code = []
    while i < len(expression.items):
      if isinstance(expression.items[i], NumberExpression):
        temporary = self.__nextTemporary()
        code.append(Store(Constant(expression.items[i].value), temporary))
      else:
        [temporary, new_code] = self.__computeIntoTemporary(expression.items[i])
        code.extend(new_code)
      if i == 0:
        prev_temporary = temporary
      else:
        function = arithmetic_functions[expression.items[i - 1].token_type]
        result_temporary = self.__nextTemporary()
        code.append(function(result_temporary, prev_temporary, temporary))
        prev_temporary = result_temporary
      i += 2
    return [prev_temporary, code]


