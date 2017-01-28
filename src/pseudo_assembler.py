#!/usr/bin/python3

from medium_level_ir import *
from util import listToString, toString, print_error

"""

Construct low level IR ("pseudo-assembly")
- Virtual registers.
- Displacement addressing.


Memory layout of objects:

FunctionContext:
link to previous function context (for restoring)
link to outer function context (for nested functions)
return value
parameters
local variables



"""

# FIXME: make sure we don't try displacement addressing with too big offsets -
# limit the size of the relevant objects (function contexts etc) and thus,
# parameter count etc. Document and enforce the limitations.

# FIXME argh, the registers are wrong when used RegisterAndOffset!!! The register is actually read, not written.


class PARegister:
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return "%" + self.name


# registersWritten vs. registersRead
# e.g., mov 4(%v0), %v1
# read: v0
# written: v1
# e.g., mov %v1, 4(%v0)
# read: v0, v1
# written: -


class PAConstant:
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return "$0x{0:x}".format(self.value)

  def registersWrittenIfTarget(self):
    return []

  def registersReadIfTarget(self):
    return []

  def registersReadIfSource(self):
    return []


class PAVirtualRegister(PARegister):
  def __init__(self, i):
    super().__init__("v" + str(i))

  def registersWrittenIfTarget(self):
    return [self]

  def registersReadIfTarget(self):
    return []

  def registersReadIfSource(self):
    return [self]


class PARegisterAndOffset:
  def __init__(self, register, offset):
    self.my_register = register
    self.offset = offset

  def __str__(self):
    return str(self.offset) + "(" + str(self.my_register) + ")"

  def registersWrittenIfTarget(self):
    # We don't write to the register, we use it for indexing.
    return []

  def registersReadIfTarget(self):
    return [self.my_register]

  def registersReadIfSource(self):
    return [self.my_register]


class PseudoAssemblerInstruction:
  def __init__(self):
    self.dead = False

  def getRegisters(self):
    return [[], []]

  def replaceRegisters(self, assigned_registers):
    pass

  @staticmethod
  def replaceRegistersIn(what, instruction, assigned_registers):
    if isinstance(what, PAConstant):
      return what
    if isinstance(what, PAVirtualRegister):
      ranges = assigned_registers[what]
      for [start, end, real_register] in ranges:
        if instruction.ix >= start and instruction.ix <= end + 1:
          return real_register
      # Maybe the register is not live at all; in that case the instruction should be removed.
      instruction.dead = True
      return None
    if isinstance(what, PARegisterAndOffset):
      what.my_register = PseudoAssemblerInstruction.replaceRegistersIn(what.my_register, instruction, assigned_registers)
      return what
    assert(False)


class PAComment(PseudoAssemblerInstruction):
  def __init__(self, text):
    super().__init__()
    self.text = text

  def __str__(self):
    return "# " + self.text


class PALabel(PseudoAssemblerInstruction):
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return self.name + ":"


class PACall(PseudoAssemblerInstruction):
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return "call " + self.name


class PACallRuntimeFunction(PACall):
  def __init__(self, name):
    super().__init__("runtime_" + name)


class PACallBuiltinFunction(PACall):
  def __init__(self, name):
    super().__init__("builtin_" + name)


class PACallUserFunction(PACall):
  def __init__(self, name):
    super().__init__("user_" + name)


class PAPush(PseudoAssemblerInstruction):
  def __init__(self, what):
    super().__init__()
    self.what = what

  def __str__(self):
    return "pushl " + str(self.what)

  def getRegisters(self):
    return [self.what.registersReadIfSource(), []]

  def replaceRegisters(self, assigned_registers):
    self.what = PseudoAssemblerInstruction.replaceRegistersIn(self.what, self, assigned_registers)


class PAClearStack(PseudoAssemblerInstruction):
  def __init__(self, value):
    super().__init__()
    self.value = value

  def __str__(self):
    return "addl $0x{0:x}, %esp".format(self.value * 4) # FIXME: magic number


class PAReturnValueToRegister(PseudoAssemblerInstruction):
  def __init__(self, register):
    super().__init__()
    self.register = register

  def __str__(self):
    return "movl %eax, " + str(self.register)

  def getRegisters(self):
    return [[], [self.register]]

  def replaceRegisters(self, assigned_registers):
    self.register = PseudoAssemblerInstruction.replaceRegistersIn(self.register, self, assigned_registers)


class PAMov(PseudoAssemblerInstruction):
  def __init__(self, what, where):
    super().__init__()
    self.what = what
    self.where = where

  def __str__(self):
    return "movl " + str(self.what) + ", " + str(self.where)

  def getRegisters(self):
    registers_read = list(set(self.what.registersReadIfSource() + self.where.registersReadIfTarget()))
    return [registers_read, self.where.registersWrittenIfTarget()]

  def replaceRegisters(self, assigned_registers):
    self.what = PseudoAssemblerInstruction.replaceRegistersIn(self.what, self, assigned_registers)
    self.where = PseudoAssemblerInstruction.replaceRegistersIn(self.where, self, assigned_registers)


class PAReturn(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    return "ret"

class PAAdd(PseudoAssemblerInstruction):
  def __init__(self, from1, to):
    super().__init__()
    assert(isinstance(to, PAVirtualRegister))
    self.from1 = from1
    self.to = to

  def __str__(self):
    return "addl " + str(self.from1) + ", " + str(self.to)

  def getRegisters(self):
    registers_read = list(set(self.from1.registersReadIfSource() + self.to.registersReadIfSource() + self.to.registersReadIfTarget()))
    return [registers_read, self.to.registersWrittenIfTarget()]

  def replaceRegisters(self, assigned_registers):
    self.from1 = PseudoAssemblerInstruction.replaceRegistersIn(self.from1, self, assigned_registers)
    self.to = PseudoAssemblerInstruction.replaceRegistersIn(self.to, self, assigned_registers)


class PseudoAssembly:
  def __init__(self, blocks, metadata):
    self.blocks = blocks
    self.metadata = metadata

  def __str__(self):
    return toString(self.blocks)


class PseudoAssemblyMetadata:
  def __init__(self, registers):
    self.registers = registers


class PseudoAssemblyBasicBlock:
  def __init__(self, id, possible_next_ids, instructions):
    self.id = id
    self.possible_next_ids = possible_next_ids
    self.instructions = instructions

  def __str__(self):
    return listToString(self.instructions, "", "", "\n")


# Creates pseudoassembly based on the medium-level IR.
class PseudoAssembler:
  def __init__(self):
    self.registers = []
    self.name_to_register = dict()

  def __nextVirtualRegister(self):
    v = PAVirtualRegister(len(self.registers))
    self.registers.append(v)
    return v

  def __virtualRegister(self, variable):
    if variable not in self.name_to_register:
      r = self.__nextVirtualRegister()
      self.name_to_register[variable] = r
    return self.name_to_register[variable]

  def __createPrologue(self):
    # FIXME: DEFINE %main as a constant
    return [PAComment("prologue"),
            PAPush(PAConstant(self.__metadata.function_context_shapes["%main"])),
            PACallRuntimeFunction("GetGlobalsTable"), # this should be a constant too
            PAReturnValueToRegister(self.__globals_table_register),
            PAClearStack(1),
            PAMov(PAConstant(0), self.__function_context_register)]

  def __createEpilogue(self):
    return []

  def __createForInstruction(self, instruction):
    if isinstance(instruction, Comment):
      return [PAComment(instruction.text)]
    if isinstance(instruction, Label):
      return [PALabel(instruction.name)]
    if isinstance(instruction, StoreConstantToGlobal):
      return [PAMov(PAConstant(instruction.value), PARegisterAndOffset(self.__globals_table_register, instruction.variable.offset))]
    if isinstance(instruction, LoadGlobalVariable):
      temp = self.__virtualRegister(instruction.to_variable)
      # FIXME: assert that to_variable is a temporary...
      return [PAMov(PARegisterAndOffset(self.__globals_table_register, instruction.from_variable.offset), temp)]

    if isinstance(instruction, CreateFunctionContextForFunction):
      # FIXME: this doesn't work for inner functions yet
      temp = self.__virtualRegister(instruction.temporary_variable)
      return [PAPush(PAConstant(self.__metadata.function_context_shapes[instruction.function.name])),
              PAPush(self.__function_context_register), # previous
              PAPush(self.__function_context_register), # outer
              PACallRuntimeFunction("CreateFunctionContext"),
              PAReturnValueToRegister(temp),
              PAClearStack(3)]
    if isinstance(instruction, AddParameterToFunctionContext):
      temp_context = self.__virtualRegister(instruction.temporary_for_function_context)
      temp = self.__virtualRegister(instruction.temporary_variable)
      # Note +2 here, because the function context contains the previous
      # function context, the outer function context and the return
      # value. FIXME: magic 4 * here again.
      return [PAMov(temp, PARegisterAndOffset(temp_context, 4 * (3 + instruction.index)))]
    if isinstance(instruction, CallFunction):
      if instruction.function.variable_type == VariableType.builtin_function:
        temp = self.__virtualRegister(instruction.temporary_for_function_context)
        new_function_context_register = self.__nextVirtualRegister()
        code = [PAPush(temp),
                PACallBuiltinFunction(instruction.function.name),
                PAClearStack(1),
                PAMov(PARegisterAndOffset(temp, 0), new_function_context_register)]
        self.__function_context_register = new_function_context_register
        return code
    if isinstance(instruction, Return):
      return [PAReturn()]

    if isinstance(instruction, AddTemporaryToTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      return [PAMov(v_from1, v_to), PAAdd(v_from2, v_to)]
    # FIXME: when we call functions, we should save and restore caller-saves
    # registers. We need to establish a convention about what are the
    # caller-saves registers anyway!

    print_error("Cannot create pseudo assembly for instruction:")
    print_error(instruction)
    assert(False)
    return []

  def create(self, ir): # FIXME: cleaner if we give the ir to the ctor
    self.__metadata = ir.metadata

    self.__globals_table_register = self.__nextVirtualRegister()
    self.__function_context_register = self.__nextVirtualRegister()

    blocks = [PseudoAssemblyBasicBlock(0, [1], self.__createPrologue())]

    for b in ir.blocks:
      code = []
      for i in b.code:
        code.extend(self.__createForInstruction(i))
      assert(b.id == len(blocks))
      blocks.append(PseudoAssemblyBasicBlock(b.id, b.next_ids, code))

    blocks.append(PseudoAssemblyBasicBlock(ir.blocks[-1].id + 1, [], self.__createEpilogue()))

    # print("Pseudo assembly program:")
    # for b in blocks:
    #   print(listToString(b.instructions, "", "", "\n"))

    return PseudoAssembly(blocks, PseudoAssemblyMetadata(self.registers))

# FIXME: calling convention: push the function context! so we don't need to reserve a register for it... and in the end of the function, go back.
