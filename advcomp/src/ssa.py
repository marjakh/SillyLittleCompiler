from cfg import CFGCreator

import sys

class Dominators:
  @staticmethod
  def computeDominators(cfg):
    for b in cfg.blocks:
      b.dominators = set()
      b.dominators.add(b)
      b.dominates = set()
      b.dominance_frontier = set()

    something_changed = True
    while something_changed:
      something_changed = False
      for b in cfg.blocks:
        new_dominators = set()
        first = True
        for pred in b.predecessors:
          if first:
            new_dominators = pred.dominators.copy()
            first = False
          else:
            new_dominators = new_dominators.intersection(pred.dominators)
        new_dominators.add(b)
        if new_dominators != b.dominators:
          something_changed = True
          b.dominators = new_dominators

    for b in cfg.blocks:
      for d in b.dominators:
        d.dominates.add(b)

    # Dominance frontier: b1 dominates a predecessor of b2 but not b2 itself.

    for b1 in cfg.blocks:
      for b2 in b1.dominates:
        for s in b2.successors:
          if s not in b1.dominates:
            b1.dominance_frontier.add(s)

class ToSSA:
  @staticmethod
  def findBlockToRename(blocks_to_rename):
    for block in blocks_to_rename:
      ok = True
      for pred in block.predecessors:
        if pred in blocks_to_rename:
          ok = False
          break
      if ok:
        return block

  @staticmethod
  def makeSSA(cfg):
    Dominators.computeDominators(cfg)

    # Add phis.
    for b in cfg.blocks:
      for instr in b.instructions:
        if instr.isDefinition():
          # The dominance frontier needs a phi node for this variable.
          # FIXME: only when it's used?
          for df in b.dominance_frontier:
            df.add_phi(instr.dest, b, instr)

    # Rename variables
    var_name_stacks = dict()
    var_name_ixs = dict()
    blocks_to_rename = set(cfg.blocks)

    # A block can be renamed when all its predecessors have been renamed.
    while len(blocks_to_rename) > 0:
      block = ToSSA.findBlockToRename(blocks_to_rename)
      ToSSA.renameBlock(block, var_name_stacks, var_name_ixs, blocks_to_rename)

  @staticmethod
  def addName(instr, var_name_stacks, var_name_ixs, names_added_by_this_block):
    var_name = instr.dest
    names_added_by_this_block.add(var_name)
    if var_name in var_name_ixs:
      use_ix = var_name_ixs[var_name]
      new_name = var_name + str(use_ix)
      var_name_ixs[var_name] = use_ix + 1
    else:
      new_name = var_name + "0"
      var_name_ixs[var_name] = 1
    if var_name in var_name_stacks:
      var_name_stacks[var_name].append(new_name)
    else:
      var_name_stacks[var_name] = [new_name]
    instr.dest = new_name

  @staticmethod
  def renameBlock(block, var_name_stacks, var_name_ixs, blocks_to_rename):
    blocks_to_rename.remove(block)
    names_added_by_this_block = set()

    for phi in block.phis.values():
      ToSSA.addName(phi, var_name_stacks, var_name_ixs, names_added_by_this_block)

    for instr in block.instructions:
      # First check the params, only after that add the new name (if any).
      # FIXME: test a = a + 1; types of instructions.
      if instr.args:
        new_args = []
        for a in instr.args:
          if a not in var_name_stacks:
            print("Instruction uses an undefined variable")
            print(instr)
            sys.exit(1)
          new_args.append(var_name_stacks[a][-1])
        instr.args = new_args
      if instr.isDefinition():
        ToSSA.addName(instr, var_name_stacks, var_name_ixs, names_added_by_this_block)

    # Recurse to all immediately dominated blocks.
    for succ in block.successors:
      if succ in block.dominates:
        ToSSA.renameBlock(succ, var_name_stacks, var_name_ixs, blocks_to_rename)

    for var_name in names_added_by_this_block:
      var_name_stacks[var_name] = var_name_stacks[var_name][:-1]

if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  for cfg in cfgs:
    ToSSA.makeSSA(cfg)
  print(CFGCreator.reconstructJSON(cfgs))

