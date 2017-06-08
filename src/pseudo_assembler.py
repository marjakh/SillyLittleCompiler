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
    if isinstance(what, PAVirtualRegister):
      if what == register:
        return new_register
      return what
    if isinstance(what, PARegisterAndOffset):
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


class PAPushCallerSaveRegisters(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    return "pushl %ecx\npushl %edx"

  def getRegisters(self):
    return [[], []]

  def replaceRegisters(self, assigned_registers):
    pass

  def replaceSpilledRegister(self, register, new_register):
    pass


class PAPopCallerSaveRegisters(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    return "popl %edx\npopl %ecx"

  def getRegisters(self):
    return [[], []]

  def replaceRegisters(self, assigned_registers):
    pass

  def replaceSpilledRegister(self, register, new_register):
    pass


class PAClearStack(PseudoAssemblerInstruction):
  def __init__(self, value):
    super().__init__()
    self.value = value

  def __str__(self):
    return "addl $0x{0:x}, %esp".format(self.value * 4) # FIXME: magic number


class PALoadSpilled(PseudoAssemblerInstruction):
  def __init__(self, register, position):
    super().__init__()
    self.register = register
    self.position = position

  def __str__(self):
    # FIXME: magic number
    return "movl -" + str(self.position * 4) + "(%ebp), " + str(self.register)

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
    # FIXME: magic number
    return "movl " + str(self.register) + ", -" + str(self.position * 4) + "(%ebp)"

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


class PAReturn(PseudoAssemblerInstruction):
  def __init__(self):
    super().__init__()

  def __str__(self):
    # FIXME: this needs to be function specific
    return "jmp epilogue"


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
  def __init__(self, blocks, metadata):
    self.blocks = blocks
    self.metadata = metadata

  def __str__(self):
    return listToString(self.blocks, "", "", "\n")

  def spill(self, register, position):
    for b in self.blocks:
      b.spill(register, position, self.metadata.registers)


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
    # FIXME: DEFINE %main as a constant
    return [PAComment("prologue"),
            PAPush(PAConstant(self.__metadata.function_context_shapes["%main"])),
            PACallRuntimeFunction("GetGlobalsTable"), # this should be a constant too
            PAReturnValueToRegister(self.__globals_table_register),
            PAClearStack(1),
            PAMov(PAConstant(0), self.__function_context_register)]

  def __createEpilogue(self):
    return []

  def __createForStore(self, store):
    if isinstance(store.what, Constant):
      if isinstance(store.where, Global):
        return [PAMov(PAConstant(store.what.value), PARegisterAndOffset(self.__globals_table_register, store.where.variable.offset))]
      if isinstance(store.where, TemporaryVariable):
        return [PAMov(PAConstant(store.what.value), self.__virtualRegister(store.where))]
    else:
      assert(isinstance(store.what, TemporaryVariable))
      if isinstance(store.where, Global):
        temp = self.__virtualRegister(store.what)
        return [PAMov(temp, PARegisterAndOffset(self.__globals_table_register, store.where.variable.offset))]

    print_error("Cannot create pseudo assembly for instruction:")
    print_error(store)
    assert(False)

  def __createForInstruction(self, instruction):
    if isinstance(instruction, Comment):
      return [PAComment(instruction.text)]

    if isinstance(instruction, Label):
      return [PALabel(instruction.name)]

    if isinstance(instruction, Store):
      return self.__createForStore(instruction)

    if isinstance(instruction, LoadGlobalVariable):
      assert(isinstance(instruction.to_variable, TemporaryVariable))
      temp = self.__virtualRegister(instruction.to_variable)
      return [PAMov(PARegisterAndOffset(self.__globals_table_register, instruction.from_variable.offset), temp)]

    if isinstance(instruction, CreateFunctionContextForFunction):
      # FIXME: this doesn't work for inner functions yet
      temp = self.__virtualRegister(instruction.temporary_variable)
      return [PAPushCallerSaveRegisters(),
              PAPush(PAConstant(self.__metadata.function_context_shapes[instruction.function.name])),
              PAPush(self.__function_context_register), # previous
              PAPush(self.__function_context_register), # outer
              PACallRuntimeFunction("CreateFunctionContext"),
              PAClearStack(3),
              PAPopCallerSaveRegisters(),
              PAReturnValueToRegister(temp)]

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
        new_function_context_register = self.registers.nextRegister()
        code = [PAPushCallerSaveRegisters(),
                PAPush(temp),
                PACallBuiltinFunction(instruction.function.name),
                PAClearStack(1),
                PAPopCallerSaveRegisters(),
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

    if isinstance(instruction, SubtractTemporaryFromTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      return [PAMov(v_from1, v_to), PASub(v_from2, v_to)]

    if isinstance(instruction, MultiplyTemporaryByTemporary):
      v_from1 = self.__virtualRegister(instruction.from_variable1)
      v_from2 = self.__virtualRegister(instruction.from_variable2)
      v_to = self.__virtualRegister(instruction.to_variable)
      return [PAMov(v_from1, self.__eax), PAMul(v_from2), PAMov(self.__eax, v_to)]

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

    print_error("Cannot create pseudo assembly for instruction:")
    print_error(instruction)
    assert(False)
    return []

  def create(self, ir): # FIXME: cleaner if we give the ir to the ctor
    self.__metadata = ir.metadata

    self.__globals_table_register = self.registers.nextRegister()
    self.__function_context_register = self.registers.nextRegister()
    self.__eax = PARegister("eax")
    self.__edx = PARegister("edx")

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
