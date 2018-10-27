#!/usr/bin/python3

from cfg_creator import CfgCreator
from constants import *
from grammar import GrammarDriver
from grammar_rules import rules
from parser import Parser
from medium_level_ir import MediumLevelIRCreator
from pseudo_assembler import PseudoAssembler
from scanner import Scanner
from scope_analyser import ScopeAnalyser
from real_assembler import RealAssembler
from util import *
from variable import Function, FunctionVariable

import sys

if __name__ == "__main__":
  input_file = open(sys.argv[1], 'r')
  source = input_file.read()
  grammar = GrammarDriver(rules)
  scanner = Scanner(source)
  p = Parser(scanner, grammar)
  p.parse()
  if not p.success:
    raise p.error

  main_variable = FunctionVariable(MAIN_NAME, MAIN_NAME, None, None)
  p.program.main_function = Function(main_variable)
  p.program.main_function.name = MAIN_NAME
  p.program.main_function.unique_name = MAIN_NAME

  sa = ScopeAnalyser(p.program)

  sa.builtins.add("print")
  sa.builtins.add("Array")
  sa.builtins.add("test_do_gc")
  sa.builtins.add("test_is_live_object")
  sa.analyse()

  if not sa.success:
    raise sa.error

  cfgc = CfgCreator(p.program)
  cfgs = cfgc.create()

  m = MediumLevelIRCreator()
  medium_level_ir = m.create(cfgs, sa.top_scope)

  # TODO: optimizations

  pa = PseudoAssembler()
  pseudo_assembly = pa.create(medium_level_ir)

  # TODO: optimizations

  ra = RealAssembler()
  real_assembly = ra.create(pseudo_assembly)

  # print("Final output:")
  print(listToString(real_assembly, "", "\n", "\n"))
