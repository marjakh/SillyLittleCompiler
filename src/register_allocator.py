#!/usr/bin/python3

from pseudo_assembler import PARegister
from real_assembler import Register
from util import listToString, toString, print_debug

"""
https://en.wikipedia.org/wiki/Register_allocation

https://www.cs.princeton.edu/courses/archive/spr05/cos320/notes/Register%20Allocation.ppt

"""

class Node:
  def __init__(self, register, assigned_register = None):
    self.register = register
    self.simplified = False
    self.conflicts = set()
    self.assigned_register = assigned_register

  def __str__(self):
    return toString(self.register)

  def addConflict(self, node):
    self.conflicts.add(node)

  def conflictCount(self):
    c = 0
    for node in self.conflicts:
      if not node.simplified:
        c += 1
    return c

  def findRegister(self, registers):
    if self.assigned_register:
      return
    for r in registers:
      # Is this register ok?
      ok = True
      for node in self.conflicts:
        if not node.simplified and node.assigned_register == r:
          ok = False
          break
      if ok:
        self.assigned_register = r
        return
    assert(False)


class RegisterAllocationDone:
  def __init__(self, assigned_registers):
    self.assigned_registers = assigned_registers


class Spill:
  def __init__(self, register):
    self.register = register


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

  @staticmethod
  def tryToAllocate(registers, real_registers):
    # FIXME: do we ever get more than one live range per register? Shouldn't we
    # in that case have used another virtual register?

    live_ranges = RegisterAllocator.computeLiveRanges(registers.registers)
    # Sort based on starting point.
    live_ranges.sort()
    # print_debug(toString(live_ranges))

    nodes = []
    for i in range(len(live_ranges)):
      nodes += [Node(live_ranges[i][2])]

    for i in range(len(live_ranges)):
      node1 = nodes[i]
      for j in range(i + 1, len(live_ranges)):
        if ((live_ranges[j][0] >= live_ranges[i][0] and live_ranges[j][0] <= live_ranges[i][1]) or
            (live_ranges[i][0] >= live_ranges[j][0] and live_ranges[i][0] <= live_ranges[j][1])):
          node2 = nodes[j]
          assert(node1 != node2)
          node1.addConflict(node2)
          node2.addConflict(node1)

    # Add a node for each real register.
    unreal_nodes = len(nodes)

    k = len(real_registers)
    for i in range(k):
      nodes += [Node(real_registers[i], real_registers[i])]

    # Add conflicts for cases where some virtual registers cannot be allocated
    # to some real registers.
    for i in range(unreal_nodes):
      node = nodes[i]
      assert(node.assigned_register == None)
      # FIXME: this is more complicated than needed because of the mismatch:
      # real registers are Registers, but in the conflict list we have the
      # corresponding PARegisters.
      for c in node.register.conflicts:
        assert(isinstance(c, PARegister))
        for j in range(k):
          real_register_node = nodes[unreal_nodes + j]
          assert(real_register_node.assigned_register != None)
          assert(isinstance(real_register_node.assigned_register, Register))
          if real_register_node.assigned_register.name == c.name:
            real_register_node.addConflict(node)
            node.addConflict(real_register_node)

    # Simplify nodes whose degree is less than k - we can always find a register for them.
    simplified = []

    stuff_to_do = True
    while stuff_to_do:
      stuff_to_do = False
      for i in range(len(nodes)):
        node = nodes[i]
        if node.simplified:
          continue
        if node.conflictCount() < k:
          # print_debug("Simplified " + str(node))
          node.simplified = True
          simplified += [node]
          stuff_to_do = True

    # If we managed to simplify everything, we're done!
    assigned_registers = dict()
    if len(simplified) == len(nodes):
      for i in range(len(simplified) - 1, -1, -1):
        node = simplified[i]
        node.findRegister(real_registers)
        node.simplified = False
        assigned_registers[node.register] = node.assigned_register
      return RegisterAllocationDone(assigned_registers)

    # Else, spill the register with the most conflicts.
    # FIXME: this strategy is bad.
    max_conflicts = 0
    max_conflict_register = None
    for node in nodes:
      if node.assigned_register:
        # Don't spill real registers.
        break
      c = node.conflictCount()
      if c > max_conflicts:
        max_conflicts = c
        max_conflict_register = node.register
    assert(max_conflicts > 0)
    # print_debug("Spilling: " + str(max_conflict_register))
    return Spill(max_conflict_register)
