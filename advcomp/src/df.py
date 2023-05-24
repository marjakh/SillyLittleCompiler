from cfg import CFGCreator

import sys

# General framework for solving data flow problems.
class DataFlow:
  @staticmethod
  def run(blocks, init_value, transform, merge):
    first = True
    worklist = []
    for b in blocks:
      if first:
        b.in_value = init_value
        first = False
      else:
        b.in_value = None
      b.out_value = None
      worklist.append(b)

    while len(worklist) > 0:
      b = worklist[0]
      worklist = worklist[1:]

      if b.out_value is None:
        old_out_len = -1
      else:
        old_out_len = len(b.out_value)

      b.in_value = merge(b, b.predecessors)
      b.out_value = transform(b)

      new_out_len = len(b.out_value)

      if old_out_len != new_out_len:
        worklist.extend(b.successors)

   # for b in blocks:
   #   print(b)
   #   print("In: " + str(b.in_value))
   #   print("Out: " + str(b.out_value))


# Config for using the data flow analysis to compute "defined variables" at any
# point of the program.
class DefinedVariables:
  @staticmethod
  def initialValue(cfg):
    ret = set()
    for arg in cfg.args:
      ret.add(arg["name"])
    return ret

  @staticmethod
  def transform(block):
    assert(isinstance(block.in_value, set))

    new_value = set()
    new_value.update(block.in_value)

    for i in block.instructions:
      if not i.dest is None:
        new_value.add(i.dest)

    return new_value

  @staticmethod
  def merge(block, predecessors):
    if len(predecessors) == 0:
      # Preserve values coming from args; those are set as the initial value.
      return block.in_value
    new_value = set()
    for b in predecessors:
      if b.out_value is None:
        continue
      new_value.update(b.out_value)
    return new_value

  @staticmethod
  def printResults(cfg):
    for b in cfg.blocks:
      print(b)
      print("In: " + str(b.in_value))
      print("Out: " + str(b.out_value))


# Config for using the data flow analysis to compute "reachable definitions" at
# any point of the program.

# The value at each point is a mapping "variable name" ->
# set of its definitions which can reach this point.
class ReachableDefinitions:
  @staticmethod
  def initialValue(cfg):
    ret = dict()
    for arg in cfg.args:
      set_of_reachable_defintions = set()
      set_of_reachable_defintions.add("this is an arg")
      ret[arg["name"]] = set_of_reachable_defintions
    return ret

  @staticmethod
  def transform(block):
    assert(isinstance(block.in_value, dict))

    current_value = dict(block.in_value)

    killed = set()
    # If a variable is used before its killed
    for i in block.instructions:
      #print(i)
      if not i.dest is None:
        # This instruction kills i.dest.
        current_value = dict(current_value)
        set_of_reachable_defintions = set()
        set_of_reachable_defintions.add(i)
        current_value[i.dest] = set_of_reachable_defintions

    return current_value

  @staticmethod
  def merge(block, predecessors):
    if len(predecessors) == 0:
      # Preserve values coming from args; those are set as the initial value.
      return block.in_value
    new_value = dict()
    for b in predecessors:
      out_value = b.out_value
      if out_value is None:
        continue
      for var_name in out_value:
        if var_name not in new_value:
          new_value[var_name] = set(out_value[var_name])
        else:
          new_value[var_name].update(out_value[var_name])
    return new_value

  @staticmethod
  def printResults(cfg):
    for b in cfg.blocks:
      current_value = dict(b.in_value)
      for i in b.instructions:
        print(i)
        if not i.args is None:
          for a in i.args:
            print("Reachable definitions for " + a + ": " + str(current_value[a]))
        # Kill if needed; this is required so that instructions inside the
        # block also get up to date data.
        if not i.dest is None:
          # This instruction kills i.dest.
          set_of_reachable_defintions = set()
          set_of_reachable_defintions.add(i)
          current_value[i.dest] = set_of_reachable_defintions


if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())

  for cfg in cfgs:
    DataFlow.run(cfg.blocks,
                 DefinedVariables.initialValue(cfg),
                 DefinedVariables.transform,
                 DefinedVariables.merge)
    #DefinedVariables.printResults(cfg)

  for cfg in cfgs:
    DataFlow.run(cfg.blocks,
                 ReachableDefinitions.initialValue(cfg),
                 ReachableDefinitions.transform,
                 ReachableDefinitions.merge)
    ReachableDefinitions.printResults(cfg)
