import json
import sys

terminators = ["jmp", "br", "ret"]

def is_label(instr):
  return "label" in instr

def is_terminator(instr):
  global terminators
  assert("op" in instr)
  op = instr["op"]
  return op in terminators

block_number = 0

class Block:
  def __init__(self):
    global block_number
    self.instructions = []
    self.successors = []
    self.block_number = block_number
    block_number += 1
    self.label = None
    self.successors = []

  def add_instruction(self, instr):
    self.instructions.append(instr)

  def __str__(self):
    s = "Block " + str(self.block_number) + " "
    if self.label is not None:
      s += str(self.label) + " "
    s += "["
    for i in self.instructions:
      s += str(i) + ", "
    s += "]"
    if len(self.successors) > 0:
      s += " Successors: ["
      for successor_block in self.successors:
        s += str(successor_block.block_number) + ", "
      s += "]"
    return s

  def set_label(self, instr):
    self.label = instr["label"]

  def is_empty(self):
    return len(self.instructions) == 0

  def last_instruction(self):
    return self.instructions[-1]

  def add_successor(self, successor):
    self.successors.append(successor)

  def get_name(self):
    if self.label is not None:
      return self.label
    return "block_{}".format(self.block_number)

class CFG:
  def __init__(self, name):
    self.blocks = []
    self.label_to_block = dict()
    self.name = name

  def add_block(self, block):
    assert(isinstance(block, Block))
    if block.is_empty():
      return
    self.blocks.append(block)
    if block.label is not None:
      self.label_to_block[block.label] = block

  def get_block(self, label):
    return self.label_to_block[label]

  def connect_blocks(self):
    for block_ix, block in enumerate(self.blocks):
      self.connect_block(block, block_ix)

  def connect_block(self, block, block_ix):
    instr = block.last_instruction()
    if "labels" in instr:
      for label in instr["labels"]:
        successor_block = self.get_block(label)
        block.add_successor(successor_block)
    elif instr["op"] == "ret":
      # No fall through.
      pass
    else:
      # Fall through to the next block.
      successor_ix = block_ix + 1
      if successor_ix < len(self.blocks):
        successor_block = self.blocks[successor_ix]
        block.add_successor(successor_block)

  def __str__(self):
    s = "CFG " + self.name + " [\n"
    for block in self.blocks:
      s+= str(block) + "\n"
    s += "]"
    return s

  def print_dot(self):
    s = "digraph {}".format(self.name) + "{\n"
    for block in self.blocks:
      s += "  " + block.get_name() + ";\n"
    for block in self.blocks:
      for succ in block.successors:
        s += "  {} -> {};\n".format(block.get_name(), succ.get_name())
    s += "}\n"
    print(s)


class CFGCreator:
  @staticmethod
  def process_func(func):
    instructions = func["instrs"]

    cfg = CFG(func["name"])
    current_block = Block()
    for instr in instructions:
      if not is_label(instr):
        current_block.add_instruction(instr)
        if is_terminator(instr):
          cfg.add_block(current_block)
          current_block = Block()
      else:
        cfg.add_block(current_block)
        current_block = Block()
        current_block.set_label(instr)

    cfg.add_block(current_block)

    cfg.connect_blocks()
    #print(cfg)
    return cfg

  @staticmethod
  def process(json_prog):
    cfgs = []
    prog = json.loads(json_prog)
    for func in prog["functions"]:
      cfg = CFGCreator.process_func(func)
      cfgs.append(cfg)
    return cfgs

  @staticmethod
  def reconstructJSON(cfgs):
    s = '{ "functions": ['
    first_cfg = True
    for cfg in cfgs:
      if not first_cfg:
        s += ", "
      first_cfg = False
      s += '{ "name": "'+ cfg.name + '", "instrs": ['
      first_instr = True
      for block in cfg.blocks:
        if block.label is not None:
          if not first_instr:
            s += ", "
          first_instr = False
          s += '{"label": "' + block.label + '"}'
        for instr in block.instructions:
          if not first_instr:
            s += ", "
          first_instr = False
          s += json.dumps(instr)
      s += "] }" # end instrs and function
    s += "] }"

    return s

if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  for cfg in cfgs:
    cfg.print_dot()
