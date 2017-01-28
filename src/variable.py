#!/usr/bin/python3

from type_enums import VariableType, ScopeType

# Variables are created during scope analysis. Note that we create separate
# variables for shadowing other variables, so name alone is not enough for
# identifying the Variable. Identifiers are resolved to variables - after that
# we know which Variable they mean. At a later point in time, we need to decide
# how the value for each Variable is stored at run time.
class Variable:
  def __init__(self, name, variable_type, allocation_scope, is_parameter=False):
    self.name = name
    self.variable_type = variable_type
    self.allocation_scope = allocation_scope
    self.is_parameter = is_parameter
    # If a variable is referred to by inner functions, it must be allocated in
    # the function context (cannot be on the stack).
    self.referred_by_inner_functions = False
    # Offset of the variable inside a function context. Filled in by later stages.
    self.offset = None

  def __str__(self):
    to_return = "Variable(" + self.name + ", "
    if self.variable_type == VariableType.variable:
      to_return += "variable, "
    elif self.variable_type == VariableType.temporary:
      to_return += "temporary, "
    elif self.variable_type == VariableType.user_function:
      to_return += "user_function, "
    elif self.variable_type == VariableType.builtin_function:
      to_return += "builtin_function, "
    else:
      assert(False)
    if not self.allocation_scope:
      assert(self.variable_type == VariableType.temporary)
      to_return += ")"
    elif self.allocation_scope.scope_type == ScopeType.function:
      to_return += "function_scope)"
    elif self.allocation_scope.scope_type == ScopeType.top:
      to_return += "top_scope)"
    else:
      assert(False)
    return to_return


# A variable which represents a function. Used for scopes.
class FunctionVariable(Variable):
  def __init__(self, name, allocation_scope, function_statement):
    # Note that allocation_scope is the scope where the function variable is
    # declared, not the scope of the function.
    super().__init__(name, VariableType.user_function, allocation_scope)
    self.function_statement = function_statement

  def __str__(self):
    return "FunctionVariable(" + self.name + ")"


# Data about functions: what are the locals, what are the parameters, etc.
class Function:
  def __init__(self, function_variable):
    self.function_variable = function_variable
    self.scope = None
    self.name = None
    # We put all variables into the function context, so that inner functions
    # can access them from there if they want to access them. Parameters are
    # copied there too. TODO: optimization: allocate locals in the stack & don't
    # copy parameters if inner functions don't need them.
    self.parameter_variables = []
    self.local_variables = []
    self.outer_function = None

  def addLocalVariable(self, v):
    self.local_variables.append(v)

  def addVariable(self, v):
    if v.variable_type == VariableType.variable:
      if v.is_parameter:
        self.parameter_variables.append(v)
      else:
        self.local_variables.append(v)

  def label(self):
    if self.name == "%main":
      return "user_main"
    return "user_function_" + self.name

