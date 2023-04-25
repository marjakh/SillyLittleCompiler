from cfg import CFGCreator

import sys

class DeadCodeEliminator:
  @staticmethod
  def eliminate(cfg):
    something_changed = True
    while something_changed:
      something_changed = False
      if DeadCodeEliminator.eliminateIfValueNotUsed(cfg):
        something_changed = True
      if DeadCodeEliminator.eliminateIfAssignmentObsoletedByAnotherAssignment(cfg):
        something_changed = True

  @staticmethod
  def eliminateIfValueNotUsed(cfg):
    # Global optimization; if we're assigning to a variable and that
    # variable is never used, eliminate the assignment.
    used_variables = set()
    for block in cfg.blocks:
      for instr in block.instructions:
        if "args" in instr:
          used_variables.update(instr["args"])

    something_changed_in_this_func = False
    something_changed = True
    while something_changed:
      something_changed = False

      for block in cfg.blocks:
        new_instructions = []
        for instr in block.instructions:
          if "dest" in instr and instr["dest"] not in used_variables:
            # Remove this instruction
            something_changed = True
            something_changed_in_this_func = True
          else:
            new_instructions.append(instr)
        block.instructions = new_instructions

    return something_changed_in_this_func

  @staticmethod
  def eliminateIfAssignmentObsoletedByAnotherAssignment(cfg):
    # Local optimization; if we're assigning to a variable and there's
    # another assignment into the same variable with no uses in between,
    # we can remove the first assignment.
    used_variables = set()
    for block in cfg.blocks:
      for instr in block.instructions:
        if "args" in instr:
          used_variables.update(instr["args"])

    something_changed = True
    something_changed_in_this_func = False
    while something_changed:
      something_changed = False

      for block in cfg.blocks:
        maybe_obsolete_assignments = dict()

        for instr in block.instructions:
          # Retrieve te values needed by the instruction -> the last assignments
          # to those are no longer candidates for removal.
          if "args" in instr:
            for a in instr["args"]:
              maybe_obsolete_assignments.pop(a, None)

          # If the instruction assigns to something, 1) potentially eliminate
          # a previous assignment, 2) record this assignment.
          if "dest" in instr:
            dest = instr["dest"]
            if dest in maybe_obsolete_assignments:
              maybe_obsolete_assignments[dest]["removeThis"] = True
              something_changed_in_this_func = True

            maybe_obsolete_assignments[dest] = instr

        new_instructions = []
        for instr in block.instructions:
          if not "removeThis" in instr:
            new_instructions.append(instr)

        block.instructions = new_instructions

    return something_changed_in_this_func


if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  for cfg in cfgs:
    DeadCodeEliminator.eliminate(cfg)

  print(CFGCreator.reconstructJSON(cfgs))
