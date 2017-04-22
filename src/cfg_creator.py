#!/usr/bin/python3

# Cfg is a mapping from function name into the control flow graph. The graph
# consists of basic blocks and each basic block consists of
# statements.

# The first phase only groups existing (high-level) statements into basic
# blocks.

# The cfg construction also eliminates dead code after a return statement.

# TODO: meaningful names for inner functions.

from parse_tree import *
from scanner import *
from type_enums import ScopeType
from util import *
from variable import Variable, FunctionVariable, Function


class BasicBlock:
  next_id = 0

  def __init__(self):
    self.statements = []
    # For printing
    self.id = BasicBlock.next_id
    BasicBlock.next_id += 1
    # If the block branches at the end, the branch is recorded here. If the
    # control flows unconditionally, it's the next basic block. Or if the
    # function ends, it's None.
    self.next = None
    self.has_returned = False

  def __str__(self):
    s = "BasicBlock(" + self.id.__str__() + ", " + listToString(self.statements) + ", "
    if isinstance(self.next, BasicBlock):
      s += "continues to block " + self.next.id.__str__()
    else:
      s += self.next.__str__()
    s += ")"
    return s


class BasicBlockBranch:
  def __init__(self, condition, true_block, false_block):
    self.condition = condition
    self.true_block = true_block
    self.false_block = false_block

  def __str__(self):
    return "BasicBlockBranch(" + self.condition.__str__() + ", true to block " + self.true_block.id.__str__() + ", false to block " + self.false_block.id.__str__() + ")"


class CfgCreatorVisitor(ParseTreeVisitor):
  def __init__(self, cfgs):
    super().__init__()
    # We're only interested in statements, and don't need to visit expressions,
    # in particular we don't want to visit the function call in the following
    # cases (in order to not generate duplicate function calls):
    # let a = foo();
    # return foo();
    # while (foo() == 0) { ... }
    # if (foo() == 0) { ... }
    # foo(bar());
    self.visit_expressions = False
    self.__basic_blocks = []
    self.__basic_block_stack = [self.__newBasicBlock()]
    self.__cfgs = cfgs # Output goes here

  def __currentBlock(self):
    return self.__basic_block_stack[-1]

  def __addStatement(self, statement):
    if self.__basic_block_stack[-1].has_returned:
      # The current basic block contains a return statement, and the rest of the
      # statements should just be ignored.
      return
    self.__basic_block_stack[-1].statements.append(statement)

  def __newBasicBlock(self):
    block = BasicBlock()
    self.__basic_blocks.append(block)
    return block

  def visitFunctionStatement(self, statement):
    # Create a new visitor for coming up with the basic blocks of the function
    v = CfgCreatorVisitor(self.__cfgs)
    # The superclass function visit the statements.
    super(CfgCreatorVisitor, v).visitFunctionStatement(statement)
    assert(len(v.__basic_block_stack) == 1)
    self.__cfgs.append([statement.function, v.__basic_blocks])

  def visitLetStatement(self, statement):
    super().visitLetStatement(statement)
    self.__addStatement(statement)

  def visitAssignmentStatement(self, statement):
    super().visitAssignmentStatement(statement)
    self.__addStatement(statement)

  def visitIfStatement(self, statement):
    # Here we need to create a branch! The current basic block ends.
    if_block = self.__newBasicBlock()
    else_block = self.__newBasicBlock() if statement.else_body else None
    after_block = self.__newBasicBlock()
    if_block.next = after_block
    if else_block:
      else_block.next = after_block

    self.__currentBlock().next = BasicBlockBranch(statement.expression, if_block,
                                                  else_block if else_block else after_block)

    self.__basic_block_stack.pop()
    self.__basic_block_stack.append(after_block)
    # else_block might be None but that's fine, we just pop it out.
    self.__basic_block_stack.append(else_block)
    self.__basic_block_stack.append(if_block)
    super().visitIfStatement(statement)

  def visitIfStatementEndBody(self, statement):
    self.__basic_block_stack.pop()

  def visitIfStatementEndElse(self, statement):
    self.__basic_block_stack.pop()

  def visitWhileStatement(self, statement):
    """We have two options how to represent the while:
    before -> dummy_only_condition_here ---f--> after
                     |      ^
                     t      |
                     |      |
                     v      |
                     body --/


    before_plus_condition -> after
           |                 ^
           v                 |
    body_plus_condition---f--/
            ^        |
            |        /
            ----t----

    We use the first one, because it's simpler (the branch is not duplicated),
    or because, frankly, we have no idea.
    """

    # TODO: when we have break and continue, this needs to change!

    dummy_block = self.__newBasicBlock()
    body_block = self.__newBasicBlock()
    after_block = self.__newBasicBlock()
    self.__currentBlock().next = dummy_block
    dummy_block.next = BasicBlockBranch(statement.expression, body_block, after_block)
    body_block.next = dummy_block

    self.__basic_block_stack.pop()
    self.__basic_block_stack.append(after_block)
    self.__basic_block_stack.append(body_block)

    super().visitWhileStatement(statement)

  def visitWhileStatementEndBody(self, statement):
    self.__basic_block_stack.pop()

  def visitFunctionCall(self, statement):
    super().visitFunctionCall(statement)
    self.__addStatement(statement)

  def visitReturnStatement(self, statement):
    self.__currentBlock().next = None

    super().visitReturnStatement(statement)

    self.__addStatement(statement)
    # If there are more statements after the return statements, they are dead
    # code. However, when the scope ends, we must continue as normal.
    self.__currentBlock().has_returned = True

class CfgCreator:
  def __init__(self, program):
    self._program = program

  def create(self):
    # Top scope statements might be sprinkled in between functions. Gather them
    # all in one place and create the cfg for the top scope in the end.
    main_body = []
    cfgs = []
    visitor = CfgCreatorVisitor(cfgs)
    for s in self._program.statements:
      if isinstance(s, FunctionStatement):
        visitor.visitFunctionStatement(s)
      else:
        main_body.append(s)
    main_statement = FunctionStatement([Token(TokenType.identifier,
                                              "%main"), [], main_body], 0)
    main_statement.function = Function(None)
    main_statement.function.name = "%main"
    visitor.visitFunctionStatement(main_statement)
    return cfgs
