#!/usr/bin/python3

from util import listToString, print_debug, toString

class LiveRangeAnalyser:
  def __init__(self):
    pass

  @staticmethod
  def analyse(function_blocks, pseudo_assembly_metadata):
    """
    For each block B:
    In_B = set of virtual registers which are live at the beginning of block B. (At first, not known.)
    Out_B = set of virtual registers which are live at the end of block B. (At first, not known.)
    Gen_B = the set of variables read in B without first being written.
    Kill_B = the set of variables written in B without having been read first.
    In_B = Gen_B U (Out_B \ Kill_B)
    Out_B = U In_C for all successors C.

    And based on that, we construct live ranges... how?
    """
    # print_debug("LiveRangeAnalyzer")
    # for b in function_blocks:
    #   print_debug("block id " + str(b.id))

    # The IDs don't start from 0, thus we need this to find the function based
    # on id from the array.
    base_id = function_blocks[0].id
    instruction_ix = 0
    for b in function_blocks:
      b.gen_set = set()
      b.kill_set = set()
      b.in_set = set() # will grow
      b.out_set = set()
      read_so_far = set()
      written_so_far = set()
      # print_debug("Basic block " + str(b.id))
      for i in b.instructions:
        # print_debug("Instruction " + str(instruction_ix) + " " + str(i))
        i.ix = instruction_ix
        instruction_ix += 1
        [read, written] = i.getRegisters()
        # print_debug("Read: " + listToString(read) + ", written: " + listToString(written))
        for r in read:
          if r not in written_so_far:
            b.gen_set.add(r)
          read_so_far.add(r)
        for r in written:
          if r not in read_so_far:
            b.kill_set.add(r)
          written_so_far.add(r)
      # print_debug("Gen: " + listToString(list(b.gen_set)))
      # print_debug("Kill: " + listToString(list(b.kill_set)))

    # print_debug("Constructing in/out sets")
    something_changed = True
    while something_changed:
      something_changed = False
      for b in function_blocks:
        # print_debug("block " + str(b.id))
        new_in_set = b.gen_set | (b.out_set - b.kill_set)
        new_out_set = set()
        # print_debug("new in set")
        # print_debug(toString(new_in_set))
        for next_id in b.possible_next_ids:
          assert(function_blocks[next_id - base_id].id == next_id)
          new_out_set = new_out_set | function_blocks[next_id - base_id].in_set
          # print_debug("new out set")
          # print_debug(toString(new_out_set))
        if new_in_set != b.in_set or new_out_set != b.out_set:
          something_changed = True
        b.in_set = new_in_set
        b.out_set = new_out_set
    # print_debug("Constructing in/out sets done")

    # for b in function_blocks:
    #   print_debug("Basic block " + str(b.id))
    #   print_debug("In: " + listToString(list(b.in_set)))
    #   print_debug("Out: " + listToString(list(b.out_set)))

    # Based on in_set and out_set, construct live ranges.
    for register in pseudo_assembly_metadata.registers.registers:
      live = set()
      currently_live = False
      maybe_range = set()
      for b in function_blocks:
        if register in b.in_set:
          maybe_range.add(b.instructions[0].ix)
        for i in b.instructions:
          [read, written] = i.getRegisters()
          if register in read:
            live.update(maybe_range)
            maybe_range = set()
          if register in written: # Note: can be also read
            # Register becomes live, but discard the current range!
            maybe_range = set()

          maybe_range.add(i.ix)

        # End of block, liveness might continue if the register is in the out set.
        if register in b.out_set:
          live.update(maybe_range)
          maybe_range = set()

      register.live = live
      # print_debug("register " + str(register))
      # print_debug(sorted(list(live)))


