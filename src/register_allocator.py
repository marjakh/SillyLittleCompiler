#!/usr/bin/python3

from util import listToString, toString, print_debug

"""
https://en.wikipedia.org/wiki/Register_allocation
"""

class Node:
  def __init__(self, reg):
    self.registers = [reg]

class RegisterAllocationDone:
  def __init__(self):
    pass

class Spill:
  def __init__(self):
    pass

class RegisterAllocator:
  def __init__(self):
    pass

  @staticmethod
  def computeLiveRanges(registers):
    # First compute live ranges.
    # Tuples: start, end, virtual register
    live_ranges = []
    for r in registers:
      live = sorted(list(r.live))
      current_range = [None, None]
      for i in live:
        if current_range[0] == None:
          current_range[0] = i
          current_range[1] = i
        elif i == current_range[1] + 1:
          # continues the current range...
          current_range[1] += 1
        else:
          # FIXME: do we ever reach this case?
          live_ranges.append([current_range[0], current_range[1], r])
          current_range[0] = i
          current_range[1] = i
      if current_range[0] != None:
        live_ranges.append([current_range[0], current_range[1], r])
    return live_ranges


  # @staticmethod
  # def allocate(registers, real_registers, spill_register_creator):
  #   # Virtual register to [[start, end, real_register]]
  #   assigned_registers = dict()
  #   for r in registers:
  #     assigned_registers[r] = []

  #   live_ranges = RegisterAllocator.computeLiveRanges(registers)
  #   # Sort based on starting point.
  #   live_ranges.sort()
  #   # print(live_ranges)

  #   # FIXME: do we ever get more than one live range per register? Shouldn't we
  #   # in that case have used another virtual register?

  #   registers_available = list(real_registers)

  #   # Iterate based on starting point
  #   active_ranges = []
  #   for [start, end, virtual_register] in live_ranges:
  #     current_instruction = start
  #     # Remove expried ranges
  #     new_active_ranges = []
  #     for [start2, end2, virtual_register2, real_register2] in active_ranges:
  #       if end2 < current_instruction:
  #         registers_available.append(real_register2)
  #       else:
  #         new_active_ranges.append([start2, end2, virtual_register2, real_register2])
  #     active_ranges = new_active_ranges

  #     # If there is a register available...
  #     # print("Handling range ")
  #     # print([start, end, virtual_register])
  #     # print(registers_available)
  #     if len(registers_available) > 0:
  #       got_register = registers_available.pop(0)
  #       assigned_registers[virtual_register].append([start, end, got_register])
  #       active_ranges.append([start, end, virtual_register, got_register])
  #     else:
  #       assert(False) # FIXME: handle this case

  #   # print("Assigned registers:")
  #   # for vr in assigned_registers:
  #   #   print(str(vr) + " " + str(assigned_registers[vr]))
  #   # print(assigned_registers)


  #   return assigned_registers

  # # Iterated Register Coalescing
  # @staticmethod
  # def allocateIRC(registers, real_registers, spill_register_creator):
  #   # Virtual register to [[start, end, real_register]]
  #   assigned_registers = dict()
  #   for r in registers:
  #     assigned_registers[r] = []

  #   # FIXME: do we ever get more than one live range per register? Shouldn't we
  #   # in that case have used another virtual register?
  #   conflicts = dict()

  #   live_ranges = RegisterAllocator.computeLiveRanges(registers)
  #   # Sort based on starting point.
  #   live_ranges.sort()
  #   print(toString(live_ranges))

  #   nodes = []
  #   for i in range(len(live_ranges)):
  #     nodes[i] = Node(live_ranges[i][2])

  #   for i in range(len(live_ranges)):
  #     node1 = nodes[i]
  #     for j in range(i + 1, len(live_ranges)):
  #       if ((live_ranges[j][0] >= live_ranges[i][0] and live_ranges[j][0] <= live_ranges[i][1]) or
  #           (live_ranges[i][0] >= live_ranges[j][0] and live_ranges[i][0] <= live_ranges[j][1])):
  #         node2 = nodes[j]
  #         assert(node1 != node2)
  #         if node1 not in conflicts:
  #           conflicts[node1] = set()
  #         if node2 not in conflicts:
  #           conflicts[node2] = set()
  #         conflicts[node1].add(node2)
  #         conflicts[node2].add(node1)
  #   print(toString(conflicts))

  #   # function IRC_color g K :
  #   # repeat
  #   #   if ∃v s.t. ¬moveRelated(v) ∧ degree(v) < K then simplify v
  #   #   else if ∃e s.t. cardinality(neighbors(first e) ∪ neighbors(second e)) < K then coalesce e
  #   #   else if ∃v s.t. moveRelated(v) then deletePreferenceEdges v
  #   #   else if ∃v s.t. ¬precolored(v) then spill v
  #   #   else return
  #   # loop

  #   stuff_to_do = True
  #   while stuff_to_do:
  #     stuff_to_do = False
  #     for i in xrange(len(registers)):
  #       reg1 = registers[i]
  #       for j in xrange(len(registers)):
  #         reg2 = registers[j]

  #   return assigned_registers

  @staticmethod
  def tryToAllocate(registers, real_registers):
    print_debug(toString(registers))
    # Virtual register to [[start, end, real_register]]
    assigned_registers = dict()
    for r in registers:
      assigned_registers[r] = []

    live_ranges = RegisterAllocator.computeLiveRanges(registers)
    # Sort based on starting point.
    live_ranges.sort()
    print_debug(toString(live_ranges))

    # FIXME: do we ever get more than one live range per register? Shouldn't we
    # in that case have used another virtual register?

    registers_available = list(real_registers)

    # Iterate based on starting point
    active_ranges = []
    for [start, end, virtual_register] in live_ranges:
      current_instruction = start
      # Remove expried ranges
      new_active_ranges = []
      for [start2, end2, virtual_register2, real_register2] in active_ranges:
        if end2 < current_instruction:
          registers_available.append(real_register2)
        else:
          new_active_ranges.append([start2, end2, virtual_register2, real_register2])
      active_ranges = new_active_ranges

      # If there is a register available...
      # print_debug("Handling range ")
      # print_debug([start, end, virtual_register])
      # print_debug(registers_available)
      if len(registers_available) > 0:
        got_register = registers_available.pop(0)
        assigned_registers[virtual_register].append([start, end, got_register])
        active_ranges.append([start, end, virtual_register, got_register])
      else:
        assert(False) # FIXME: handle this case

    # print_debug("Assigned registers:")
    # for vr in assigned_registers:
    #   print_debug(str(vr) + " " + str(assigned_registers[vr]))
    # print_debug(assigned_registers)


    return assigned_registers
