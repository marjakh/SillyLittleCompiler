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


# Does mostly register allocation. Also, we need to take care of saving and
# restoring caller-saves registers.
class RealAssembler:
  def __init__(self):
    self.__eax = Register("eax")
    self.__ebx = Register("ebx")
    self.__real_registers = [self.__ebx, Register("ecx"), Register("edx")]
    self.__ebp = Register("ebp")
    self.__esp = Register("esp")

  # FIXME: refactor out common parts, move code to pseudo assembler.
  def __createMainPrologue(self, spill_position, local_counts, string_count):
    code = [Label("user_code"),
            PAComment("prologue"),
            # Crete stack frame for the main function.
            # 1) Saved ebp (new ebp will point to it)
            PAPush(self.__ebp),
            PAPush(self.__ebx),
            PAMov(self.__esp, self.__ebp),
            # 2) Stack frame marker
            PAPush(PAConstant(0xc0decafe)),
            # 3) Function context pointer
            PAPush(PAConstant(string_count)),
            PALea(PAVariable("strings"), self.__eax),
            PAPush(self.__eax),
            PAPush(PAConstant(local_counts)),
            PACallRuntimeFunction("CreateMainFunctionContext"),
            PABuiltinOrRuntimeFunctionReturnValueToRegister(self.__eax),
            PAClearStack(3),
            PAPush(self.__eax),
            # Set spill count in function context
            PASub(PAConstant(PTR_TAG), self.__eax),
            PAMov(PAConstant(spill_position), PARegisterAndOffset(self.__eax, FUNCTION_CONTEXT_SPILL_COUNT_OFFSET * POINTER_SIZE)),
            #4) Space for spills
            PAComment("Number of spills: " + str(spill_position)),
            PASub(PAConstant(spill_position * POINTER_SIZE), self.__esp),
            PAMov(self.__esp, self.__eax),
            PAPush(PAConstant(spill_position * POINTER_SIZE)),
            PAPush(PAConstant(0)),
            PAPush(self.__eax),
            PACall("memset"),
            PAClearStack(3),
            #5) Let runtime know about stack high
            PAPush(self.__ebp),
            PACallRuntimeFunction("SetStackHigh"),
            PAClearStack(1)]
    for r in self.__real_registers:
      code.append(PAMov(PAConstant(0), r))
    return code

  def __createFunctionPrologue(self, function_name, spill_position):
    code = [Label("user_function_" + function_name),
            PAComment("prologue"),
            PAPop(self.__ebx), # Return address
            PAPop(self.__eax), # Function context
            PAPush(self.__ebx), # Push return address back
            # Crete stack frame for the function.
            # 1) Saved self.__ebp (new self.__ebp will point to it)
            PAPush(self.__ebp),
            PAMov(self.__esp, self.__ebp),
            # 2) Stack frame marker
            PAPush(PAConstant(0xc0decafe)),
            # 3) Function context pointer
            PAPush(self.__eax),
            # Set spill count in function context
            PASub(PAConstant(PTR_TAG), self.__eax),
            PAMov(PAConstant(spill_position), PARegisterAndOffset(self.__eax, FUNCTION_CONTEXT_SPILL_COUNT_OFFSET * POINTER_SIZE)),
            #4) Space for spills
            PAComment("Number of spills: " + str(spill_position)),
            PASub(PAConstant(spill_position * POINTER_SIZE), self.__esp),
            PAMov(self.__esp, self.__eax),
            PAPush(PAConstant(spill_position * POINTER_SIZE)),
            PAPush(PAConstant(0)),
            PAPush(self.__eax),
            PACall("memset"),
            PAClearStack(3)]
    return code

  def create(self, pseudo_assembly):
    # FIXME: when we have functions, we need to run the register allocator for each separately.

    program = [GlobalDeclaration("user_code"),
               Label("strings"),
               ".ascii " + pseudo_assembly.metadata.string_table.dump()]

    for [function, function_blocks] in pseudo_assembly.functions_and_blocks:
      # FIXME: function name needs to refer the outer function. Add tests that
      # we call the correct inner function.

      # print_debug("Analyzing " + function.name)
      # If we cannot assign registers for all temporary variables, we need to
      # spill some registers.
      spill_position = 1 # FIXME: why not 0?
      assigned_registers = None
      while True:
        # print_debug("Pseudo assembly:")
        # print_debug(pseudo_assembly)

        LiveRangeAnalyser.analyse(function_blocks, pseudo_assembly.metadata)

        action = RegisterAllocator.tryToAllocate(pseudo_assembly.metadata.registers,
                                                 self.__real_registers)
        if isinstance(action, Spill):
          # print_debug("Spilling " + str(action.register) + " to position " + str(spill_position))
          # FIXME: ugly, refactor.
          pseudo_assembly.spill(action.register, spill_position, function_blocks)
          spill_position += 1
        elif isinstance(action, RegisterAllocationDone):
          assigned_registers = action.assigned_registers
          break
        else:
          assert(False)

      if function.name == MAIN_NAME:
        program.extend(self.__createMainPrologue(spill_position, pseudo_assembly.metadata.function_param_and_local_counts[MAIN_NAME], pseudo_assembly.metadata.string_table.stringCount()))
      else:
        program.extend(self.__createFunctionPrologue(function.function_variable.unique_name(), spill_position))

      for b in function_blocks:
        for i in b.instructions:
          i.replaceRegisters(assigned_registers)
          i.setSpillCount(spill_position)
          if not i.dead:
            program.append(i)
      if function.name == MAIN_NAME:
        program.append(Label("main_epilogue"))
        program.append(PAMov(self.__ebp, self.__esp))
        program.append(PAPop(self.__ebx)) # Restore saved ebx
        program.append(PAPop(self.__ebp)) # Restore saved ebp
      else:
        program.append(Label("user_function_" + function.function_variable.unique_name() + "_epilogue"))
        program.append(PAMov(self.__ebp, self.__esp))
        program.append(PAPop(self.__ebp)) # Restore saved ebp
      program.append(PARealReturn())

    for [handler_label, error_index] in pseudo_assembly.error_handlers:
      program += [PALabel(handler_label),
                  PAPush(PAConstant(error_index)),
                  PACallRuntimeFunction("Error")]
    return program
