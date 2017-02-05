#!/usr/bin/python3

from live_range_analyser import LiveRangeAnalyser
from pseudo_assembler import *
from register_allocator import RegisterAllocator, RegisterAllocationDone, Spill
from util import listToString, print_debug

class RealAssemblerInstruction:
  def __init__(self):
    pass

class Label:
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return self.name + ": "


class GlobalDeclaration:
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return ".globl " + self.name


class CallRuntimeFunction(RealAssemblerInstruction):
  def __init__(self, name):
    super().__init__()
    self.name = name

  def __str__(self):
    return ""

class Register:
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return "%" + self.name


class SpillRegister(Register):
  def __init__(self, ix):
    super().__init__("Spill_" + str(ix))


# FIXME: might be dead
class SpillRegisterCreator:
  def __init__(self):
    self.ix = 0

  def getSpillRegister(self):
    self.ix += 1
    return SpillRegister(self.ix)



# Does mostly register allocation. Also, we need to take care of saving and
# restoring caller-saves registers.
class RealAssembler:

  @staticmethod
  def create(pseudo_assembly):
    # FIXME: when we have functions, we need to run the register allocator for each separately.

    real_registers = [Register("ebx"), Register("ecx"), Register("edx")]

    # If we cannot assign registers for all temporary variables, we need to
    # spill some registers.
    spill_position = 0
    assigned_registers = None
    while True:
      # print_debug("Pseudo assembly:")
      # print_debug(pseudo_assembly)

      LiveRangeAnalyser.analyse(pseudo_assembly)

      action = RegisterAllocator.tryToAllocate(pseudo_assembly.metadata.registers,
                                               real_registers)
      if isinstance(action, Spill):
        # print_debug("Spilling " + str(action.register))
        pseudo_assembly.spill(action.register, spill_position)
        spill_position += 1
      elif isinstance(action, RegisterAllocationDone):
        assigned_registers = action.assigned_registers
        break
      else:
        assert(False)

    program = [
      Label("text"),
      GlobalDeclaration("user_code"),
      Label("user_code")]

    for b in pseudo_assembly.blocks:
      for i in b.instructions:
        i.replaceRegisters(assigned_registers)
        if not i.dead:
          program.append(i)

    return program
