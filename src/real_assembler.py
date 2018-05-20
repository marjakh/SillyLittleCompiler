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

    eax = Register("eax")
    real_registers = [Register("ebx"), Register("ecx"), Register("edx")]
    ebp = Register("ebp")
    esp = Register("esp")

    # If we cannot assign registers for all temporary variables, we need to
    # spill some registers.
    spill_position = 1
    assigned_registers = None
    while True:
      # print_debug("Pseudo assembly:")
      # print_debug(pseudo_assembly)

      LiveRangeAnalyser.analyse(pseudo_assembly)

      action = RegisterAllocator.tryToAllocate(pseudo_assembly.metadata.registers,
                                               real_registers)
      if isinstance(action, Spill):
        # print_debug("Spilling " + str(action.register) + " to position " + str(spill_position))
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
      Label("user_code")
    ]

    # FIXME: create function descriptor
    # FIXME: each function needs this.
    program.append(Label("main_prologue"))
    # Crete stack frame for the main function.
    # 1) Saved ebp (new ebp will point to it)
    program.append(PAPush(ebp))
    program.append(PAMov(esp, ebp))
    # 2) Stack frame marker
    program.append(PAPush(PAConstant(0xc0decafe)))
    # 3) Function context pointer
    program.append(PAPush(PAConstant(pseudo_assembly.metadata.function_local_counts["%main"])))
    program.append(PAPush(PAConstant(spill_position)))
    program.append(PACallRuntimeFunction("CreateMainFunctionContext"))
    program.append(PAReturnValueToRegister(eax))
    program.append(PAClearStack(2))
    program.append(PAPush(eax))
    #4) Space for spills
    # FIXME: magic number
    program.append(PAComment("Number of spills: " + str(spill_position)))
    program.append(PASub(PAConstant(spill_position * 4), esp))
    program.append(PAMov(esp, eax))
    program.append(PAPush(PAConstant(spill_position * 4)))
    program.append(PAPush(PAConstant(0)))
    program.append(PAPush(eax))
    program.append(PACall("memset"))
    program.append(PAAdd(PAConstant(3 * 4), esp))
    for r in real_registers:
      program.append(PAMov(PAConstant(0), r))
    for b in pseudo_assembly.blocks:
      for i in b.instructions:
        i.replaceRegisters(assigned_registers)
        i.setSpillCount(spill_position)
        if not i.dead:
          program.append(i)
    program.append(Label("main_epilogue"))
    program.append(PAMov(ebp, esp))
    program.append(PAPop(ebp)) # Restore saved ebp
    program.append(PARealReturn())

    return program
