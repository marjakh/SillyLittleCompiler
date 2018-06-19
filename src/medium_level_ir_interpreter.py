#!/usr/bin/python3

from cfg_creator import CfgCreator
from grammar import GrammarDriver
from grammar_rules import rules
from parser import Parser
from medium_level_ir import MediumLevelIRCreator
from scanner import Scanner
from scope_analyser import ScopeAnalyser

import sys

class MediumLevelIRInterpreter:
  def __init__(self):
    self.grammar = grammar
    self.source = source

  def run(self):
    # TODO: global output
    pass


if __name__ == "__main__":
  input_file = open(sys.argv[1], 'r')
  source = input_file.read()
  grammar = GrammarDriver(rules)
  scanner = Scanner(source)
  p = Parser(scanner, grammar)
  p.parse()
  if not p.success:
    raise p.error
  sa = ScopeAnalyser(p.program)

  sa.builtins.add("write")
  sa.analyse()

  if not sa.success:
    raise sa.error

  cfgc = CfgCreator(p.program)
  cfgs = cfgc.create()

  pa = MediumLevelIRCreator()
  medium_level_ir = pa.create(cfgs, sa.top_scope)

  # i = MediumLevelIRInterpreter()
  # output = i.run().strip()
  # print(output)
