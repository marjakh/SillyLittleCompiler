from cfg import CFGCreator

import sys

class DeadCodeEliminator:
  @staticmethod
  def eliminate(cfg):
    cfg = DeadCodeEliminator.eliminateIfValueNotUsed(cfg)
    return cfg

  @staticmethod
  def eliminateIfValueNotUsed(cfg):
    # Global optimization; if we're assigning to a variable and that
    # variable is never used, eliminate the assignment.
    used_variables = set()
    for block in cfg.blocks:
      for instr in block.instructions:
        if "args" in instr:
          used_variables.update(instr["args"])

    something_changed = True
    while something_changed:
      something_changed = False

      for block in cfg.blocks:
        new_instructions = []
        for instr in block.instructions:
          if "dest" in instr and instr["dest"] not in used_variables:
            # Remove this instruction
            something_changed = True
          else:
            new_instructions.append(instr)
        block.instructions = new_instructions

if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  new_cfgs = []
  for cfg in cfgs:
    new_cfg = DeadCodeEliminator.eliminate(cfg)
    new_cfgs.append(cfg)
  print(CFGCreator.reconstructJSON(new_cfgs))
