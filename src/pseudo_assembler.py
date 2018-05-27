#!/usr/bin/python3

from medium_level_ir import *
from util import listToString, toString, print_error
from constants import *

"""

Construct low level IR ("pseudo-assembly")
- Virtual registers.
- Displacement addressing.


Division:
https://www.csie.ntu.edu.tw/~acpang/course/asm_2004/slides/chapt_07_PartIISolve.pdf

"""

# FIXME: make sure we don't try displacement addressing with too big offsets -
# limit the size of the relevant objects (function contexts etc) and thus,
# parameter count etc. Document and enforce the limitations.

class Register:
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return "%" + self.name


class PARegister(Register):
  def __init__(self, name):
    super().__init__(name)

  def registersWrittenIfTarget(self):
    return []

  def registersReadIfTarget(self):
    return []

  def registersReadIfSource(self):
    return []


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
    # Which real registers this virtual register cannot use.
    self.conflicts = set()

  def addConflict(self, register):
    self.conflicts.add(register)

  def registersWrittenIfTarget(self):
    return [self]

  def registersReadIfTarget(self):
    return []

  def registersReadIfSource(self):
    return [self]

  # Comparison needed for sorting live ranges in register allocator. Order
  # doesn't really matter.
  def __lt__(self, other):
    return self.name < other.name


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


class PARegisters:
  def __init__(self):
    self.registers = []

  def nextRegister(self):
    v = PAVirtualRegister(len(self.registers))
    self.registers.append(v)
    return v

  def __str__(self):
    return toString(self.registers)


class PseudoAssemblerInstruction:
  def __init__(self):
    self.dead = False

  def getRegisters(self):
    return [[], []]

  def replaceRegisters(self, assigned_registers):
    pass

  def replaceSpilledRegister(self, register, new_register):
    pass

  # There's one special instruction which needs to know the spill count in order
  # to function properly.
  def setSpillCount(self, spill_count):
    pass

  @staticmethod
  def replaceRegistersIn(what, instruction, assigned_registers):
    if isinstance(what, PAConstant):
      return what
    if isinstance(what, PAVirtualRegister):
      if what in assigned_registers:
        return assigned_registers[what]
      # Maybe the register is not live at all; in that case the instruction should be removed.
      instruction.dead = True
      return None
    if isinstance(what, PARegisterAndOffset):
      what.my_register = PseudoAssemblerInstruction.replaceRegistersIn(what.my_register, instruction, assigned_registers)
      return what
    if isinstance(what, PARegister):
      return what
    assert(False)

  @staticmethod
  def replaceSpilledRegisterIn(what, register, new_register):
    if isinstance(what, PAConstant):
      return what
    elif isinstance(what, PAVirtualRegister):
      if what == register:
        return new_register
      return what
    elif isinstance(what, PARegister):
      return what
    elif isinstance(what, PARegisterAndOffset):
      what.my_register = PseudoAssemblerInstruction.replaceSpilledRegisterIn(what.my_register, register, new_register)
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


class PACustom(PseudoAssemblerInstruction):
  def __init__(self, code):
    super().__init__()
    self.code = code

  def __str__(self):
    return self.code


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
    super().__init__("user_function_" + name)


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

  def replaceSpilledRegister(self, register, new_register):
    self.what = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.what, register, new_register)


class PAPop(PseudoAssemblerInstruction):
  def __init__(self, where):
    super().__init__()
    self.where = where

  def __str__(self):
    return "popl " + str(self.where)

  def getRegisters(self):
    return [[], self.where.registersReadIfTarget()]

  def replaceRegisters(self, assigned_registers):
    self.where = PseudoAssemblerInstruction.replaceRegistersIn(self.where, self, assigned_registers)

  def replaceSpilledRegister(self, register, new_register):
    self.where = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.where, register, new_register)


# Before calling into runtime, we need to push *all* registers (not just
# caller-save registers), since the GC might want to change them.
class PAPushAllRegisters(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    # FIXME: refactor; don't hardcode register names here.
    return "pushl %ebx\npushl %ecx\npushl %edx"


class PAPopAllRegisters(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    # FIXME: refactor; don't hardcode register names here.
    return "popl %edx\npopl %ecx\npopl %ebx"


class PAClearStack(PseudoAssemblerInstruction):
  def __init__(self, value):
    super().__init__()
    self.value = value

  def __str__(self):
    return "addl $0x{0:x}, %esp".format(self.value * POINTER_SIZE)


def spillPositionToEbpOffsetString(position):
  return str((SPILL_AREA_FROM_EBP_OFFSET - position) * POINTER_SIZE) + "(%ebp)"


class PALoadSpilled(PseudoAssemblerInstruction):
  def __init__(self, register, position):
    super().__init__()
    self.register = register
    self.position = position

  def __str__(self):
    return "movl " + spillPositionToEbpOffsetString(self.position) + ", " + str(self.register) + " # Load spilled"

  def replaceRegisters(self, assigned_registers):
    self.register = PseudoAssemblerInstruction.replaceRegistersIn(self.register, self, assigned_registers)

  def replaceSpilledRegister(self, register, new_register):
    self.register = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.register, register, new_register)

  def getRegisters(self):
    return [[], [self.register]]


class PAStoreSpilled(PseudoAssemblerInstruction):
  def __init__(self, register, position):
    super().__init__()
    self.register = register
    self.position = position

  def __str__(self):
    return "movl " + str(self.register) + ", " + spillPositionToEbpOffsetString(self.position) + " # Store spilled"

  def replaceRegisters(self, assigned_registers):
    self.register = PseudoAssemblerInstruction.replaceRegistersIn(self.register, self, assigned_registers)

  def replaceSpilledRegister(self, register, new_register):
    self.register = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.register, register, new_register)

  def getRegisters(self):
    return [[self.register], []]


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

  def replaceSpilledRegister(self, register, new_register):
    self.register = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.register, register, new_register)


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

  def replaceSpilledRegister(self, register, new_register):
    self.what = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.what, register, new_register)
    self.where = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.where, register, new_register)


class PATopLevelReturn(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    return "jmp main_epilogue"


class PAReturn(PseudoAssemblerInstruction):
  def __init__(self, function_name):
    super().__init__()
    self.function_name = function_name

  def __str__(self):
    return "jmp user_function_" + self.function_name + "_epilogue"

class PARealReturn(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    return "ret"


class PACmp(PseudoAssemblerInstruction):
  def __init__(self, left, right):
    super().__init__()
    self.left = left
    self.right = right

  def __str__(self):
    return "cmp " + str(self.left) + ", " + str(self.right)

  def getRegisters(self):
    registers_read = list(set(self.left.registersReadIfSource() + self.right.registersReadIfSource()))
    return [registers_read, []]

  def replaceRegisters(self, assigned_registers):
    self.left = PseudoAssemblerInstruction.replaceRegistersIn(self.left, self, assigned_registers)
    self.right = PseudoAssemblerInstruction.replaceRegistersIn(self.right, self, assigned_registers)

  def replaceSpilledRegister(self, register, new_register):
    self.left = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.left, register, new_register)
    self.right = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.right, register, new_register)


class PAJumpInstruction(PseudoAssemblerInstruction):
  def __init__(self, op, label):
    super().__init__()
    self.op = op
    self.label = label

  def __str__(self):
    return self.op + " " + self.label


class PAJump(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("jmp", label)


class PAJumpEquals(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("je", label)


class PAJumpNotEquals(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("jne", label)


class PAJumpLessThan(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("jl", label)


class PAJumpLessOrEquals(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("jle", label)


class PAJumpGreaterThan(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("jg", label)


class PAJumpGreaterOrEquals(PAJumpInstruction):
  def __init__(self, label):
    super().__init__("jge", label)


jump_types = dict()
jump_types["=="] = PAJumpEquals
jump_types["!="] = PAJumpNotEquals
# This is wonky, because.. the cmp instruction is the other way around?
jump_types[">"] = PAJumpLessThan
jump_types[">="] = PAJumpLessOrEquals
jump_types["<"] = PAJumpGreaterThan
jump_types["<="] = PAJumpGreaterOrEquals


# Superclass for instructions such as add or sub which operate on one register
# and one other operand.
class PseudoAssemblerInstructionOperatingOnRegister(PseudoAssemblerInstruction):
  def __init__(self, source, target, name):
    super().__init__()
    assert(isinstance(target, Register))
    self.source = source
    self.target = target
    self.name = name

  def __str__(self):
    return self.name + " " + str(self.source) + ", " + str(self.target)

  def getRegisters(self):
    registers_read = list(set(self.source.registersReadIfSource() + self.target.registersReadIfSource() + self.target.registersReadIfTarget()))
    return [registers_read, self.target.registersWrittenIfTarget()]

  def replaceRegisters(self, assigned_registers):
    self.source = PseudoAssemblerInstruction.replaceRegistersIn(self.source, self, assigned_registers)
    self.target = PseudoAssemblerInstruction.replaceRegistersIn(self.target, self, assigned_registers)

  def replaceSpilledRegister(self, register, new_register):
    self.source = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.source, register, new_register)
    self.target = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.target, register, new_register)


class PAAdd(PseudoAssemblerInstructionOperatingOnRegister):
  def __init__(self, from1, to):
    # FIXME: from and to are not the correct names
    super().__init__(from1, to, "addl")


class PASub(PseudoAssemblerInstructionOperatingOnRegister):
  def __init__(self, from1, to):
    # FIXME: from and to are not the correct names
    super().__init__(from1, to, "subl")


# Pseudo assembler instruction with one implicit source (constant, register or
# register + offset) and an implicit target register.
class PseudoAssemblerInstructionWithSource(PseudoAssemblerInstruction):
  def __init__(self, source, name):
    super().__init__()
    self.source = source
    self.name = name

  def __str__(self):
    return self.name + " " + str(self.source)

  def getRegisters(self):
    registers_read = list(set(self.source.registersReadIfSource()))
    return [registers_read, []]

  def replaceRegisters(self, assigned_registers):
    self.source = PseudoAssemblerInstruction.replaceRegistersIn(self.source, self, assigned_registers)

  def replaceSpilledRegister(self, register, new_register):
    self.source = PseudoAssemblerInstruction.replaceSpilledRegisterIn(self.source, register, new_register)

class PAMul(PseudoAssemblerInstructionWithSource):
  def __init__(self, source):
    super().__init__(source, "imull")


class PADiv(PseudoAssemblerInstructionWithSource):
  def __init__(self, source):
    super().__init__(source, "idivl")



class PseudoAssembly:
  def __init__(self, functions_and_blocks, metadata):
    self.functions_and_blocks = functions_and_blocks
    self.metadata = metadata

  def __str__(self):
    return listToString(self.functions_and_blocks, "", "", "\n")

  def spill(self, register, position, blocks):
    for b in blocks:
      b.spill(register, position, self.metadata.registers)


class PseudoAssemblyMetadata:
  def __init__(self, registers, function_local_counts, function_param_counts):
    self.registers = registers
    self.function_local_counts = function_local_counts
    self.function_param_counts = function_param_counts


class PseudoAssemblyBasicBlock:
  def __init__(self, id, possible_next_ids, instructions):
    self.id = id
    self.possible_next_ids = possible_next_ids
    self.instructions = instructions

  def __str__(self):
    return listToString(self.instructions, "", "", "\n")

  def spill(self, register, position, registers):
    new_instructions = []
    for i in self.instructions:
      [read, written] = i.getRegisters()
      if register not in read and register not in written:
        new_instructions += [i]
      else:
        new_register = registers.nextRegister()
        if register in read:
          # Read into a new temporary register from the spill position.
          new_instructions += [PALoadSpilled(new_register, position)]
        i.replaceSpilledRegister(register, new_register)
        new_instructions += [i]
        if register in written:
          new_instructions += [PAStoreSpilled(new_register, position)]
    self.instructions = new_instructions


# Creates pseudoassembly based on the medium-level IR.
class PseudoAssembler:
  def __init__(self):
    self.registers = PARegisters()
    self.name_to_register = dict()

  def __virtualRegister(self, variable):
    if variable not in self.name_to_register:
      r = self.registers.nextRegister()
      self.name_to_register[variable] = r
    return self.name_to_register[variable]

  def __createPrologue(self):
    # FIXME: move code here
    return [PAComment("prologue")]

  def __createEpilogue(self):
    return []

  def __cannotCreate(self, instruction):
    print_error("Cannot create pseudo assembly for instruction:")
    print_error(instruction)
    assert(False)

  def __getFunctionContext(self, function_context):
    return PAMov(self.__function_context_location, function_context)

  def __createForLoad(self, load):
    assert(isinstance(load.where, TemporaryVariable))
    temp = self.__virtualRegister(load.where)
    if isinstance(load.what, Local):
      function_context = self.registers.nextRegister()
      # FIXME: take params size into account
      return [self.__getFunctionContext(function_context),
              PAMov(PARegisterAndOffset(function_context, load.what.variable.offset + FUNCTION_CONTEXT_HEADER_SIZE), temp)]

    if isinstance(load.what, Array):
      [address_register, code] = self.__createLoadArray(load.what)
      return [PAComment("Load from array")] + code + [PAMov(PARegisterAndOffset(address_register, 0), temp), PAComment("Load from array done")]

    # FIXME: implement the rest
    self.__cannotCreate(load)

  def __createLoadArray(self, array):
    assert(isinstance(array.base, StoreOrLoadTarget))
    code = [PAComment("Computing array address")]
    if isinstance(array.base, Local):
      # local[%temp] or local[constant]

      # FIXME: refactor this; the array is just an address which is the value of
      # the local variable, so we should just load that value. Create a Load
      # with this temp as load.where and array.base as load.what.
      function_context = self.registers.nextRegister()
      address_register = self.registers.nextRegister()
      code += [self.__getFunctionContext(function_context),
               PAMov(PARegisterAndOffset(function_context, array.base.variable.offset + FUNCTION_CONTEXT_HEADER_SIZE), address_register)]

      [address_register2, index_code] = self.__createArrayIndexingCode(address_register, array.index)
      return [address_register2, code + index_code]
    elif isinstance(array.base, Array):
      [address_register, load_array_code] = self.__createLoadArray(array.base)
      read_from_array_register = self.registers.nextRegister()
      reference_array_code = [PAMov(PARegisterAndOffset(address_register, 0), read_from_array_register)]
      [address_register2, index_code] = self.__createArrayIndexingCode(read_from_array_register, array.index)
      return [address_register2, code + load_array_code + reference_array_code + index_code]
    assert(False)

  def __createArrayIndexingCode(self, address_register, index):
    code = [PAComment("Indexing array")]
    if isinstance(index, Constant):
      # FIXME: does this actually happen ever?
      assert(False)
    else:
      assert(isinstance(index, TemporaryVariable))
      pointer_size_register = self.registers.nextRegister()
      address_register2 = self.registers.nextRegister()
      code += [PAMov(self.__virtualRegister(index), self.__eax),
               PAMov(PAConstant(POINTER_SIZE), pointer_size_register),
               PAPush(self.__edx),
               PAMov(PAConstant(0), self.__edx),
               PAMul(pointer_size_register),
               PAPop(self.__edx),
               PAMov(self.__eax, address_register2),
               PAAdd(address_register, address_register2)]
      pointer_size_register.addConflict(self.__edx)
    code += [PAComment("Computing array address done")]
    return [address_register2, code]

  def __createForStore(self, store):
    assert(isinstance(store.where, StoreOrLoadTarget) or isinstance(store.where, TemporaryVariable))
    if isinstance(store.where, Array):
      [address_register, code] = self.__createLoadArray(store.where)
      code.insert(0, PAComment("Store to array"))
      if isinstance(store.what, Constant):
        code += [PAMov(PAConstant(store.what.value), PARegisterAndOffset(address_register, 0)), PAComment("Store to array done")]
        return code
      else:
        assert(isinstance(store.what, TemporaryVariable))
        code += [PAMov(self.__virtualRegister(store.what), PARegisterAndOffset(address_register, 0)), PAComment("Store to array done")]
        return code

    if isinstance(store.what, Constant):
      if isinstance(store.where, Local):
        function_context = self.registers.nextRegister()
        return [self.__getFunctionContext(function_context),
                PAMov(PAConstant(store.what.value), PARegisterAndOffset(function_context, store.where.variable.offset + FUNCTION_CONTEXT_HEADER_SIZE))]
      if isinstance(store.where, TemporaryVariable):
        return [PAMov(PAConstant(store.what.value), self.__virtualRegister(store.where))]
    else:
      assert(isinstance(store.what, TemporaryVariable))
      if isinstance(store.where, Local):
        temp = self.__virtualRegister(store.what)
        function_context = self.registers.nextRegister()
        return [self.__getFunctionContext(function_context),
                PAMov(temp, PARegisterAndOffset(function_context, store.where.variable.offset + FUNCTION_CONTEXT_HEADER_SIZE))]

    # FIXME: implement the rest
    self.__cannotCreate(store)


  def __createForInstruction(self, instruction):
    return [PAComment("Instruction: " + str(instruction))] + self.__createForInstructionWithoutComment(instruction)

  def __createForInstructionWithoutComment(self, instruction):
    if isinstance(instruction, Comment):
      return [PAComment(instruction.text)]

    if isinstance(instruction, Label):
      return [PALabel(instruction.name)]

    if isinstance(instruction, Load):
      return self.__createForLoad(instruction)

    if isinstance(instruction, Store):
      return self.__createForStore(instruction)

    if isinstance(instruction, CreateFunctionContextForFunction):
      # FIXME: this doesn't work for inner functions yet
      temp = self.__virtualRegister(instruction.temporary_variable)
      return [PAPushAllRegisters(),
              PAPush(self.__ebp), # stack low
              PAPush(PAConstant(self.__metadata.function_local_counts[instruction.function.unique_name()])),
              PAPush(PAConstant(self.__metadata.function_param_counts[instruction.function.unique_name()])),
              PAPush(self.__function_context_location), # outer
              PACallRuntimeFunction("CreateFunctionContext"),
              PAClearStack(4),
              PAPopAllRegisters(),
              PAReturnValueToRegister(temp)]

    if isinstance(instruction, AddParameterToFunctionContext):
      temp_context = self.__virtualRegister(instruction.temporary_for_function_context)
      temp = self.__virtualRegister(instruction.temporary_variable)
      # Note +3 here, because the function context contains the spill count,
      # the outer function context and the params size.
      return [PAMov(temp, PARegisterAndOffset(temp_context, POINTER_SIZE * (FUNCTION_CONTEXT_PARAMS_OFFSET + instruction.index)))]

    if isinstance(instruction, CallFunction):
      if instruction.function.variable_type == VariableType.builtin_function:
        # Don't create a full-blown stack frame; the C side will do
        # it. Especially, the function context is passed as a normal parameter,
        # but not saved into the stack next to ebp.
        temp = self.__virtualRegister(instruction.temporary_for_function_context)
        code = [PAComment("Calling builtin function"),
                PAComment("Registers"),
                PAPushAllRegisters(),
                PAComment("Stack low and function context"),
                PAPush(self.__ebp), # stack low
                PAPush(temp),
                PACallBuiltinFunction(instruction.function.name),
                PAClearStack(2),
                PAPopAllRegisters(),
                PAComment("Calling builtin function done")]
        return code
      elif instruction.function.variable_type == VariableType.user_function:
        temp = self.__virtualRegister(instruction.temporary_for_function_context)
        code = [PAComment("Calling user function"),
                PAComment("Push all registers"),
                PAPushAllRegisters(),
                PAComment("Function context"),
                PAPush(temp),
                PACallUserFunction(instruction.function.name),
                PAClearStack(1),
                PAComment("Pop all registers"),
                PAPopAllRegisters(),
                PAComment("Calling user function done")]
        return code
      else:
        self.__cannotCreate(instruction)

    if isinstance(instruction, Return):
      if self.__function.name == "%main":
        return [PATopLevelReturn()]
      return [PAReturn(self.__function.name)]

    if isinstance(instruction, AddTemporaryToTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      return [PAMov(v_from1, v_to), PAAdd(v_from2, v_to)]

    if isinstance(instruction, SubtractTemporaryFromTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      return [PAMov(v_from1, v_to), PASub(v_from2, v_to)]

    if isinstance(instruction, MultiplyTemporaryByTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      v_from2.addConflict(self.__edx)
      return [PAMov(v_from1, self.__eax),
              PAPush(self.__edx),
              PAMov(PAConstant(0), self.__edx),
              PAMul(v_from2),
              PAPop(self.__edx),
              PAMov(self.__eax, v_to)]

    if isinstance(instruction, DivideTemporaryByTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      # FIXME: this is inefficient. We might not need to push edx.
      return [PAMov(v_from1, self.__eax), PAPush(self.__edx), PACustom("cdq"), PADiv(v_from2), PAPop(self.__edx), PAMov(self.__eax, v_to)]

    if isinstance(instruction, TestWithOperator):
      v_left = self.__virtualRegister(instruction.left)
      v_right = self.__virtualRegister(instruction.right)
      jump_type = jump_types[instruction.op]
      return [PACmp(v_left, v_right), jump_type(instruction.true_label), PAJump(instruction.false_label)]

    if isinstance(instruction, Goto):
      return [PAJump(instruction.label)]

    if isinstance(instruction, GetReturnValue):
      # This ignores the function context parameter. Maybe refactor and actually
      # read the return value from the function context.
      v = self.__virtualRegister(instruction.temporary_variable)
      return [PAReturnValueToRegister(v)]

    self.__cannotCreate(instruction)

  def create(self, ir): # FIXME: cleaner if we give the ir to the ctor
    self.__metadata = ir.metadata

    self.__eax = PARegister("eax")
    self.__edx = PARegister("edx")
    self.__esp = PARegister("esp")
    self.__ebp = PARegister("ebp")
    self.__function_context_location = PARegisterAndOffset(self.__ebp, FUNCTION_CONTEXT_FROM_EBP_OFFSET * POINTER_SIZE)

    output = []
    running_id = 0
    for [function, function_blocks] in ir.functions_and_blocks:
      # print_debug("Pseudo assembler: Function " + str(function.name))
      self.__function = function
      blocks = [PseudoAssemblyBasicBlock(running_id, [running_id + 1], self.__createPrologue())]
      running_id = running_id + 1
      id_correction = running_id - function_blocks[0].id
      # print_debug("id correction " + str(id_correction))
      for b in function_blocks:
        code = []
        for i in b.code:
          code.extend(self.__createForInstruction(i))
        # print_debug("has block " + str(b.id))
        blocks.append(PseudoAssemblyBasicBlock(running_id, [i + id_correction for i in b.next_ids], code))
        running_id = running_id + 1

      blocks.append(PseudoAssemblyBasicBlock(running_id, [], self.__createEpilogue()))
      running_id = running_id + 1

      output.append([function, blocks])
      # print_debug("Pseudo assembly for function " + function.name)
      # for b in blocks:
      #   print_debug(listToString(b.instructions, "", "", "\n"))

    return PseudoAssembly(output, PseudoAssemblyMetadata(self.registers, self.__metadata.function_local_counts, self.__metadata.function_param_counts))

