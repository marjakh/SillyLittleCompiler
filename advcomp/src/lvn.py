from cfg import CFGCreator
from dce import DeadCodeEliminator

import sys

class Value:
  def __init__(self, op, args):
    self.op = op
    self.args = args

  def __str__(self):
    # Return a string which can be used as a key
    first = True
    s = self.op + "["
    for a in self.args:
      if not first:
        s += ", "
      first = False
      s += str(a)
    s += "]"
    return s

# FIXME: value canonicalization

class LocalValueNumbering:
  @staticmethod
  def optimize(cfg):
    for block in cfg.blocks:
      LocalValueNumbering.optimizeBlock(block)

  @staticmethod
  def constructValue(instr, value_table, environment):
    if instr["op"] == "const":
      return Value(instr["op"], [instr["value"]])

    # FIXME: what to do with "id"?

    assert("args" in instr)
    arg_value_ids = []
    for arg in instr["args"]:
      # Find this arg from the table
      if not arg in environment:
        # This basic block doesn't know about this variable; it might be coming
        # from another basic block. Insert a dummy entry for it.
        ix = len(value_table)
        value_table.append([None, arg])
        environment[arg] = ix

      arg_value_id = environment[arg]
      arg_value_ids.append(arg_value_id)
    return Value(instr["op"], arg_value_ids)

  @staticmethod
  def updateInstruction(instr, value, value_table, environment):
    if not "args" in instr:
      return
    args = []
    for a in value.args:
      canonical_home_variable = value_table[a][1]
      args.append(canonical_home_variable)
    instr["args"] = args

  @staticmethod
  def optimizeBlock(block):

    # Value table:
    # id | value | canonical home variable
    # Now the ids are just indices
    value_table = []

    # Lookup table from str(value)s to value table ids
    value_table_lookup = dict()

    # Environment:
    # Mapping from variable names to value table ids
    environment = dict()

    for instr in block.instructions:
      #print(instr)

      if not "op" in instr:
        # Labels and stuff
        continue

      value = LocalValueNumbering.constructValue(instr, value_table, environment)
      #print("value is " + str(value))

      if "dest" in instr:
        str_value = str(value)
        # Check if the value is already in the value table
        if str_value in value_table_lookup:
          ix = value_table_lookup[str_value]
        else:
          ix = len(value_table)
          value_table.append([value, instr["dest"]])
          value_table_lookup[str_value] = ix

        environment[instr["dest"]] = ix

      # Reconstruct the instruction
      LocalValueNumbering.updateInstruction(instr, value, value_table, environment)


if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  for cfg in cfgs:
    LocalValueNumbering.optimize(cfg)
    DeadCodeEliminator.eliminate(cfg)

  print(CFGCreator.reconstructJSON(cfgs))
