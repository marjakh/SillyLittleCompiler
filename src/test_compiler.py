#!/usr/bin/python3

from grammar import GrammarDriver
from grammar_rules import rules
from interpreter import Interpreter

import os
import subprocess

if __name__ == '__main__':
  skipped = 0

  # Read all input files in tests/, run the prog with the interpreter, ensure
  # that the output matches the corresponding output file.
  test_path = "compiler_tests"
  files = [f for f in os.listdir(test_path) if os.path.isfile(os.path.join(test_path, f)) and f.endswith("in")]
  good_files = [f for f in files if not f.startswith("error_")]
  good_files.sort()
  bad_files = [f for f in files if f.startswith("error_")]
  bad_files.sort()

  for input_file_name in good_files:
    output_file_name = input_file_name[:-2] + "out"
    print("Running test " + input_file_name)
    if not os.path.isfile(os.path.join(test_path, output_file_name)):
      print("Corresponding output file " + output_file_name + " not found")
      exit(1)
    input_file_path = os.path.join(test_path, input_file_name)
    input_file = open(input_file_path, 'r')
    input = input_file.read()
    if input.startswith("SKIP"):
      print("SKIPPED")
      skipped += 1
      continue
    input_file.close()
    output_file = open(os.path.join(test_path, output_file_name), 'r')
    expected_output = output_file.read().strip()
    output_file.close()

    try:
      compile_output = subprocess.check_output(["src/compile.sh", input_file_path])
    except subprocess.CalledProcessError as e:
      print("Compilation failed")
      print(e.output)
      print("That was the output")
      exit(1)
    output = fixme

    if output != expected_output:
      print("Got output:\n" + output)
      print("Wanted output:\n" + expected_output)
      exit(1)
    assert(output == expected_output)

#  for input_file_name in bad_files:
#    output_file_name = input_file_name[:-2] + "out"
#    print("Running test " + input_file_name)
#    if not os.path.isfile(os.path.join(test_path, output_file_name)):
#      print("Corresponding output file " + output_file_name + " not found")
#      exit(1)
#    input_file = open(os.path.join(test_path, input_file_name), 'r')
#    input = input_file.read()
#    if input.startswith("SKIP"):
#      print("SKIPPED")
#      skipped += 1
#      continue
#    output_file = open(os.path.join(test_path, output_file_name), 'r')
#    expected_output = output_file.read().strip()

#    grammar = GrammarDriver(rules)

#    try:
#      i = Interpreter(grammar, input)
#      i.run()
#    except BaseException as e:
#      output = e.__class__.__name__
#    else:
#      print("Expecting an error, got none")
#      exit(1)

#    if output != expected_output:
#      print("Got output:\n" + output)
#      print("Wanted output:\n" + expected_output)
#      exit(1)
#    assert(output == expected_output)

  if skipped > 0:
    print("Some tests skipped")
    exit(1)

  print("All OK!")
  exit(0)
