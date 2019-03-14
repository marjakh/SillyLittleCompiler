#!/usr/bin/python3

from scanner import Scanner, TokenType
from util import list_to_string, print_debug

class Type:
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return self.name


class String(Type):
  def __init__(self):
    super().__init__("string")

  def allows_sub_type(self):
    return False


class Int(Type):
  def __init__(self):
    super().__init__("int")

  def allows_sub_type(self):
    return False


class Any(Type):
  def __init__(self):
    super().__init__("any")

  def allows_sub_type(self):
    return False


class ClassType(Type):
  def __init__(self, name):
    assert(isinstance(name, str))
    super().__init__(name)

  def allows_sub_type(self):
    return True


class FunctionType(Type):
  def __init__(self, parameter_types, return_type):
    assert(isinstance(return_type, Type))
    assert(isinstance(parameter_types, TypeList) or parameter_types is None)
    parameter_types = parameter_types or TypeList(None)
    name = list_to_string(parameter_types.items) + " -> " + str(return_type)
    super().__init__(name)
    self.return_type = return_type
    self.parameter_types = parameter_types.items

  def allows_sub_type(self):
    return False


def dispatch_type_template(base_type, sub_type):
  if sub_type is None:
    return base_type
  if base_type.allows_sub_type() == False:
    raise SyntaxError("Invalid type: subtype not allowed")
  return TypeTemplate(base_type, sub_type)


class TypeTemplate(Type):
  def __init__(self, base_type, sub_type):
    assert(isinstance(base_type, Type))
    assert(isinstance(sub_type, Type))
    name = str(base_type) + "<" + str(sub_type) + ">"
    super().__init__(name)
    self.base_type = base_type
    self.sub_type = sub_type


class TypeList:
  def __init__(self, items):
    if items is None:
      self.items = []
    else:
      assert(len(items) == 2)
      assert(isinstance(items[0], Type))
      self.items = [items[0]]
      if items[1] is not None:
        assert(isinstance(items[1], TypeListContinuation))
        self.items.extend(items[1].items)


class TypeListContinuation:
  def __init__(self, items):
    assert(len(items) == 2)
    assert(isinstance(items[0], Type))
    self.items = [items[0]]
    if items[1] is not None:
      assert(isinstance(items[1], TypeListContinuation))
      self.items.extend(items[1].items)


string_type = String()
int_type = Int()
any_type = Any()


def identifier_to_type(s):
  if s == "string":
    return string_type
  elif s == "int":
    return int_type
  elif s == "any":
    return any_type
  else:
    return ClassType(s)
