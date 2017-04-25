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
  return offset

def computeVariableOffsetsForTopScope(top_scope):
  offset = 0
  for v in top_scope.variables:
    if v.variable_type == VariableType.variable:
      v.offset = offset
      offset += 4
  return offset


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
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return "goto " + self.name


class Test(MediumLevelIRInstruction):
  def __init__(self, temporary_variable, true_label, false_label):
    super().__init__()
    self.temporary_variable = temporary_variable
    self.true_label = true_label
    self.false_label = false_label

  def __str__(self):
    return "test " + self.temporary_variable.name + "? " + self.true_label + " : " + self.false_label


class StoreConstant(MediumLevelIRInstruction):
  def __init__(self, variable, value, comment):
    super().__init__()
    self.variable = variable
    self.value = value
    self.comment = comment

  def __str__(self):
    return self.variable.name + " = " + str(self.value) + " # " + self.comment


class StoreConstantToLocal(StoreConstant):
  def __init__(self, variable, value, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(variable, value, "store local, offset = " + str(variable.offset))


class StoreConstantToGlobal(StoreConstant):
  def __init__(self, variable, value, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(variable, value, "store global, offset = " + str(variable.offset))


class StoreConstantToParameter(StoreConstant):
  def __init__(self, variable, value, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(variable, value, "assign to parameter, offset = " + str(variable.offset))


class StoreConstantToOuterFunctionLocal(StoreConstant):
  def __init__(self, variable, value, levels_up):
    assert(levels_up != None)
    super().__init__(variable, value, "assign to outer function local")
    self.levels_up = levels_up

  def __str__(self):
    return super().__str__() + " " + str(self.levels_up) + " levels up, offset = " + str(self.variable.offset)


class StoreConstantToOuterFunctionParameter(StoreConstant):
  def __init__(self, variable, value, levels_up):
    assert(levels_up != None)
    super().__init__(variable, value, "assign to outer function parameter")
    self.levels_up = levels_up

  def __str__(self):
    return super().__str__() + " " + str(self.levels_up) + " levels up, offset = " + str(self.variable.offset)


class StoreConstantToTemporary(StoreConstant):
  def __init__(self, temporary_variable, value, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(temporary_variable, value, "assign to temporary")


class StoreTemporary(MediumLevelIRInstruction):
  def __init__(self, variable, temporary_variable, comment):
    super().__init__()
    self.variable = variable
    self.temporary_variable = temporary_variable
    self.comment = comment

  def __str__(self):
    return self.variable.name + " = " + str(self.temporary_variable.name) + " # " + self.comment


class StoreTemporaryToLocal(StoreTemporary):
  def __init__(self, variable, temporary_variable, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(variable, temporary_variable, "assign to local")


class StoreTemporaryToGlobal(StoreTemporary):
  def __init__(self, variable, temporary_variable, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(variable, temporary_variable, "assign to global")


class StoreTemporaryToParameter(StoreTemporary):
  def __init__(self, variable, temporary_variable, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(variable, temporary_variable, "assign to parameter")


class StoreTemporaryToOuterFunctionLocal(StoreTemporary):
  def __init__(self, variable, temporary_variable, levels_up):
    super().__init__(variable, temporary_variable, "assign to outer function local")
    self.levels_up = levels_up

  def __str__(self):
    return super().__str__() + " " + str(self.levels_up) + " levels up"


class StoreTemporaryToOuterFunctionParameter(StoreTemporary):
  def __init__(self, variable, temporary_variable, levels_up):
    super().__init__(variable, temporary_variable, "assign to outer function parameter")
    self.levels_up = levels_up

  def __str__(self):
    return super().__str__() + " " + str(self.levels_up) + " levels up"

store_functions = dict();
store_functions["constant"] = dict();
store_functions["constant"]["local"] = dict();
store_functions["constant"]["local"]["not_parameter"] = StoreConstantToLocal;
store_functions["constant"]["local"]["parameter"] = StoreConstantToParameter;
store_functions["constant"]["outer"] = dict();
store_functions["constant"]["outer"]["not_parameter"] = StoreConstantToOuterFunctionLocal;
store_functions["constant"]["outer"]["parameter"] = StoreConstantToOuterFunctionParameter;
store_functions["constant"]["global"] = dict();
store_functions["constant"]["global"]["not_parameter"] = StoreConstantToGlobal;

store_functions["not_constant"] = dict();
store_functions["not_constant"]["local"] = dict();
store_functions["not_constant"]["local"]["not_parameter"] = StoreTemporaryToLocal;
store_functions["not_constant"]["local"]["parameter"] = StoreTemporaryToParameter;
store_functions["not_constant"]["outer"] = dict();
store_functions["not_constant"]["outer"]["not_parameter"] = StoreTemporaryToOuterFunctionLocal;
store_functions["not_constant"]["outer"]["parameter"] = StoreTemporaryToOuterFunctionParameter;
store_functions["not_constant"]["global"] = dict();
store_functions["not_constant"]["global"]["not_parameter"] = StoreTemporaryToGlobal;


class LoadVariable(MediumLevelIRInstruction):
  def __init__(self, to_variable, from_variable, comment):
    super().__init__()
    self.to_variable = to_variable
    self.from_variable = from_variable
    self.comment = comment

  def __str__(self):
    return self.to_variable.name + " = " + self.from_variable.name + " # " + self.comment


class LoadLocalVariable(LoadVariable):
  def __init__(self, to_variable, from_variable, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(to_variable, from_variable, "load local")


class LoadGlobalVariable(LoadVariable):
  def __init__(self, to_variable, from_variable, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(to_variable, from_variable, "load global")


class LoadParameter(LoadVariable):
  def __init__(self, to_variable, from_variable, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(to_variable, from_variable, "load parameter")


class LoadOuterFunctionLocalVariable(LoadVariable):
  def __init__(self, to_variable, from_variable, levels_up):
    assert(levels_up != None)
    super().__init__(to_variable, from_variable, "load outer function local")
    self.levels_up = levels_up

  def __str__(self):
    return super().__str__() + " " + str(self.levels_up) + " levels up"


class LoadOuterFunctionParameter(LoadVariable):
  def __init__(self, to_variable, from_variable, levels_up):
    assert(levels_up != None)
    super().__init__(to_variable, from_variable, "load outer function parameter")
    self.levels_up = levels_up

  def __str__(self):
    return super().__str__() + " " + str(self.levels_up) + " levels up"


class LoadFunction(MediumLevelIRInstruction):
  def __init__(self, to_variable, function, loader_function_name):
    super().__init__()
    self.to_variable = to_variable
    self.function = function
    self.loader_function_name = loader_function_name

  def __str__(self):
    return self.to_variable.name + " = " + self.loader_function_name + "(" + self.function.name


class LoadGlobalFunction(LoadFunction):
  def __init__(self, to_variable, function, extra_parameter=None):
    assert(extra_parameter == None)
    super().__init__(to_variable, function, "GlobalFunctionObject")

  def __str__(self):
    return super().__str__() + ")"


# The inner function in question can be directly inside this function or inner
# function of some of the outer functions.
class LoadInnerFunction(LoadFunction):
  def __init__(self, to_variable, function, levels_up=0):
    if not levels_up:
      levels_up = 0
    self.levels_up = levels_up
    super().__init__(to_variable, function, "CreateClosure")

  def __str__(self):
    return super().__str__() + ", " + str(self.levels_up) + ")"


load_functions = dict();
load_functions["variable"] = dict();
load_functions["variable"]["local"] = dict();
load_functions["variable"]["local"]["not_parameter"] = LoadLocalVariable;
load_functions["variable"]["local"]["parameter"] = LoadParameter;
load_functions["variable"]["outer"] = dict();
load_functions["variable"]["outer"]["not_parameter"] = LoadOuterFunctionLocalVariable;
load_functions["variable"]["outer"]["parameter"] = LoadOuterFunctionParameter;
load_functions["variable"]["global"] = dict();
load_functions["variable"]["global"]["not_parameter"] = LoadGlobalVariable;
load_functions["function"] = dict();
load_functions["function"]["local"] = dict();
load_functions["function"]["local"]["not_parameter"] = LoadInnerFunction;
load_functions["function"]["outer"] = dict();
load_functions["function"]["outer"]["not_parameter"] = LoadInnerFunction;
load_functions["function"]["global"] = dict();
load_functions["function"]["global"]["not_parameter"] = LoadGlobalFunction;


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


class CreateFunctionContext(MediumLevelIRInstruction):
  def __init__(self, temporary_variable, function, call_string):
    super().__init__()
    self.temporary_variable = temporary_variable
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
    self.function_context_shapes = dict()


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
        metadata.function_context_shapes[f.name] = computeVariableOffsetsForTopScope(top_scope)
      else:
        metadata.function_context_shapes[f.name] = computeVariableOffsetsForFunction(f)

    addBuiltinFunctionShapes(metadata.function_context_shapes)

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
      assert(isinstance(block.next, BasicBlockBranch))
      condition = block.next.condition
      assert(isinstance(condition, BooleanExpression))
      # TODO: shortcut if left / right sides of the expression are simpler
      # (e.g., numbers)
      # TODO: shortcut if always true / always false (already one level up!)
      [temporary1, code1] = self.__computeIntoTemporary(condition.items[0])
      output.extend(code1)
      [temporary2, code2] = self.__computeIntoTemporary(condition.items[2])
      output.extend(code2)
      [temporary3, code3] = self.__computeComparisonIntoTemporary(temporary1, temporary2, condition.items[1])
      output.extend(code3)
      output.append(Test(temporary3, "block_" + str(block.next.true_block.id), "block_" + str(block.next.false_block.id)))
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
      return self.__createForAssignmentStatement(statement)
    if isinstance(statement, AssignmentStatement):
      return self.__createForAssignmentStatement(statement)

    # TODO: optimization: if there are repated calls to a function, we can reuse
    # the function context, we just need to nullify relevant fields.
    if isinstance(statement, FunctionCall):
      temporary_for_function_context = self.__nextTemporary()
      if statement.is_direct():
        code = [CreateFunctionContextForFunction(temporary_for_function_context, statement.resolved_function)]
      else:
        code = [CreateFunctionContextFromVariable(temporary_for_function_context, statement.resolved_function)]
      for i in range(len(statement.parameters)):
        # TODO: optimization: if the parameter is trivial, we don't need to store it into a temporary
        [temporary, temporary_code] = self.__computeIntoTemporary(statement.parameters[i])
        code += temporary_code + [AddParameterToFunctionContext(temporary_for_function_context, i, temporary)]
      code += [CallFunction(statement.resolved_function, temporary_for_function_context)]
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
    print("Unable to create medium level IR for statement:")
    print(statement)
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
    """

    # Find the proper assignment function...
    [variable_or_function, scope, is_parameter, extra_parameter] = self.__findVariableSpecs(statement.resolved_variable)
    assert(variable_or_function == "variable")

    if isinstance(statement.expression, NumberExpression):
      is_constant = "constant"
      return [store_functions[is_constant][scope][is_parameter](statement.resolved_variable, statement.expression.value, extra_parameter)]
    else:
      # Complex expressions.
      is_constant = "not_constant"
      [temporary, temporary_code] = self.__computeIntoTemporary(statement.expression);
      return temporary_code + [store_functions[is_constant][scope][is_parameter](statement.resolved_variable, temporary, extra_parameter)]

  def __findVariableSpecs(self, variable):
    extra_parameter = None
    if variable.variable_type == VariableType.variable:
      variable_or_function = "variable"
    else:
      variable_or_function = "function" # FIXME: builtins
    if variable.allocation_scope == self.__current_function.scope:
      scope = "local"
    elif variable.allocation_scope.scope_type == ScopeType.top:
      scope = "global"
    else:
      scope = "outer"
      extra_parameter = 1
      outer = self.__current_function.outer_function
      assert(outer)
      while variable.allocation_scope != outer.scope:
        extra_parameter += 1
        outer = outer.outer_function
        assert(outer)

    if variable.is_parameter:
      is_parameter = "parameter"
    else:
      is_parameter = "not_parameter"
    return [variable_or_function, scope, is_parameter, extra_parameter]

  def __computeIntoTemporary(self, expression):
    if isinstance(expression, NumberExpression):
      # TODO: optimization: many of these can be shortcut.
      temporary = self.__nextTemporary()
      return [temporary, [StoreConstantToTemporary(temporary, expression.value)]]

    if isinstance(expression, FunctionCall):
      temporary_for_function_context = self.__nextTemporary()
      if expression.is_direct():
        code = [CreateFunctionContextForFunction(temporary_for_function_context, expression.resolved_function)]
      else:
        code = [CreateFunctionContextFromVariable(temporary_for_function_context, expression.resolved_function)]
      for i in range(len(expression.parameters)):
        # TODO: optimization: if the parameter is trivial, we don't need to store it into a temporary
        [temporary, temporary_code] = self.__computeIntoTemporary(expression.parameters[i])
        code += temporary_code + [AddParameterToFunctionContext(temporary_for_function_context, i, temporary)]
      temporary_for_return_value = self.__nextTemporary()
      code += [CallFunction(expression.resolved_function, temporary_for_function_context),
               GetReturnValue(temporary_for_return_value, temporary_for_function_context)]
      return [temporary_for_return_value, code]

    if isinstance(expression, VariableExpression):
      temporary = self.__nextTemporary()
      [variable_or_function, scope, is_parameter, extra_parameter] = self.__findVariableSpecs(expression.resolved_variable)
      return [temporary, [load_functions[variable_or_function][scope][is_parameter](temporary, expression.resolved_variable, extra_parameter)]]

    if isinstance(expression, AddExpression) or isinstance(expression, MultiplyExpression):
      return self.__accumulateAddExpressionOrMultiplyExpression(expression)

    print("Unable to create pseudo assembly for expression:")
    print(expression)
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
        code.append(StoreConstantToTemporary(temporary, expression.items[i].value))
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


