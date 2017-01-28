from enum import Enum

class VariableType(Enum):
  variable = 0
  temporary = 1
  user_function = 2
  builtin_function = 3


class ScopeType(Enum):
  top = 0
  function = 1
  sub = 2
