from cfg import CFGCreator
from dce import DeadCodeEliminator

import sys

# FIXME: this is wrong for function calls; they're not pure so we cannot skip
# them.

# FIXME: DCE for function calls is probably wrong, too.

class Value:
  def __init__(self, op, args):
    self.op = op
    self.args = args

    # Commutative operations:
    if op == "mul" or op == "add":
      self.args.sort()

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


class LocalValueNumbering:
  @staticmethod
  def optimize(cfg):
    for block in cfg.blocks:
      LocalValueNumbering.optimizeBlock(block)

  @staticmethod
  def constructValue(instr, value_table, environment):
    if instr["op"] == "const":
      return Value(instr["op"], [instr["value"]])

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
    #print("updateInstruction")
    #print(instr)
    #print(value)
    #print(value_table)
    #print(environment)

    if not "args" in instr:
      return

    op = instr["op"]
    if op == "id":
      if LocalValueNumbering.updateIdInstruction(instr, value, value_table, environment):
        # updateIdInstruction handled it
        return
    elif op == "add" or op == "mul" or op == "sub" or op == "div":
      if LocalValueNumbering.maybeConstantFold(instr, value, value_table, environment):
        return

    args = []
    for a in value.args:
      canonical_home_variable = value_table[a][1]
      args.append(canonical_home_variable)
    instr["args"] = args

  @staticmethod
  def updateIdInstruction(instr, value, value_table, environment):
    #print("updateIdInstruction")
    #print(instr)
    #print(value)
    #print(value_table)
    #print(environment)

    assert(len(value.args) == 1)
    ix = value.args[0]

    # Check if the value at "ix" is a const.
    replacement_value = value_table[ix][0]
    if not replacement_value is None and replacement_value.op == "const":
      instr["op"] = "const"
      assert(len(replacement_value.args) == 1)
      instr["value"] = replacement_value.args[0]
      del instr["args"]
      return True

    return False

  @staticmethod
  def maybeConstantFold(instr, value, value_table, environment):
    #print("maybeConstantFold")
    #print(instr)
    #print(value)
    #print(value_table)
    #print(environment)

    assert(len(value.args) == 2)
    ix1 = value.args[0]
    ix2 = value.args[1]

    # Check if the value at "ix" is a const.
    replacement_value1 = value_table[ix1][0]
    if replacement_value1 is None or replacement_value1.op != "const":
      return False
    replacement_value2 = value_table[ix2][0]
    if replacement_value2 is None or replacement_value2.op != "const":
      return False

    # Update the instruction
    op = instr["op"]

    assert(len(replacement_value1.args) == 1)
    value1 = replacement_value1.args[0]
    assert(len(replacement_value2.args) == 1)
    value2 = replacement_value2.args[0]

    if op == "add":
      value = value1 + value2
    elif op == "sub":
      value = value1 - value2
    elif op == "mul":
      value = value1 * value2
    elif op == "div":
      value = value1 / value2
    instr["op"] = "const"
    instr["value"] = value
    del instr["args"]

    # Update the value of the row ix of "dest" in the value_table.
    ix = environment[instr["dest"]]
    value_table[ix][0] = Value("const", [value])

    return True

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

    # For generating new variable names
    var_ix = 0

    for i_ix, instr in enumerate(block.instructions):
      #print(instr)

      if not "op" in instr:
        # Labels and stuff
        continue

      value = LocalValueNumbering.constructValue(instr, value_table, environment)
      #print("value is " + str(value))

      if "dest" in instr:
        dest = instr["dest"]

        # If dest will be overwritten later, it cannot be used as a canonical
        # home variable that easily. Prepare for that situation by renaming
        # dest now.
        dest_will_be_overwritten = False
        for i2_ix in range(i_ix + 1, len(block.instructions)):
          instr2 = block.instructions[i2_ix]
          if "dest" in instr2 and instr2["dest"] == dest:
            dest_will_be_overwritten = True
            break

        if dest_will_be_overwritten:
          # Rename this variable and also rename all uses before the overwriting
          # instruction.
          old_dest = dest
          dest = "variable" + str(var_ix)
          var_ix += 1

          instr["dest"] = dest

          for i2_ix in range(i_ix + 1, len(block.instructions)):
            instr2 = block.instructions[i2_ix]
            if "args" in instr2:
              new_args = []
              for a in instr2["args"]:
                if a == old_dest:
                  new_args.append(dest)
                else:
                  new_args.append(a)
              instr2["args"] = new_args
            # This has to be done last, since it's possible the overwriting
            # insruction also uses old_dest.
            if "dest" in instr2 and instr2["dest"] == old_dest:
              break

        str_value = str(value)
        if value.op == "id":
          # If we encounter
          # b: int = id a;
          # make b point to the row where a is stored.
          ix = value.args[0]
        elif str_value in value_table_lookup:
          ix = value_table_lookup[str_value]
        else:
          ix = len(value_table)
          value_table.append([value, dest])
          value_table_lookup[str_value] = ix

        environment[dest] = ix

      # Reconstruct the instruction
      LocalValueNumbering.updateInstruction(instr, value, value_table, environment)



if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  for cfg in cfgs:
    LocalValueNumbering.optimize(cfg)
    DeadCodeEliminator.eliminate(cfg)

  print(CFGCreator.reconstructJSON(cfgs))
