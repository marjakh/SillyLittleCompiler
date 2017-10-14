#!/usr/bin/python3

from cfg_creator import CfgCreator
from grammar import GrammarDriver
from grammar_rules import rules
from parser import Parser
from medium_level_ir import MediumLevelIRCreator
from pseudo_assembler import PseudoAssembler
from scanner import Scanner
from scope_analyser import ScopeAnalyser
from real_assembler import RealAssembler
from util import *

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
  sa = ScopeAnalyser(p.program)

  sa.builtins.add("write")
  sa.builtins.add("id")
  sa.builtins.add("nth")
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

  real_assembly = RealAssembler.create(pseudo_assembly)

#  output = NamedTemporaryFile()
#  output.write(bytes(listToString(real_assembly, "", "\n", "\n"), "UTF-8"))
#  # FIXME: allow the caller to pass the object file name
#  # print(output.name)
#  output.flush()
#  call(["as", "-32", "-ggstabs", "-o" "temp.o", output.name])
#  output.close()

  # print("Final output:")
  print(listToString(real_assembly, "", "\n", "\n"))
