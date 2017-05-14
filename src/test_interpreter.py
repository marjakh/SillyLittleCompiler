#!/usr/bin/python3

from grammar import GrammarDriver
from grammar_rules import rules
from interpreter import Interpreter

import os

def run_tests_in(test_path):
  skipped = 0
  # Read all input files in the directory, run the prog with the interpreter,
  # ensure that the output matches the corresponding output file.
  files = [f for f in os.listdir(test_path) if os.path.isfile(os.path.join(test_path, f)) and f.endswith("in")]
  good_files = [f for f in files if not f.startswith("error_")]
  good_files.sort()
  bad_files = [f for f in files if f.startswith("error_")]
  bad_files.sort()

  for input_file_name in good_files:
    input_file_path = os.path.join(test_path, input_file_name)
    output_file_path = os.path.join(test_path, input_file_name[:-2] + "out")
    print("Running test " + input_file_path)
    if not os.path.isfile(output_file_path):
      print("Corresponding output file " + output_file_path + " not found")
      exit(1)
    input_file = open(input_file_path, 'r')
    input = input_file.read()
    if input.startswith("SKIP"):
      print("SKIPPED")
      skipped += 1
      continue
    output_file = open(output_file_path, 'r')
    expected_output = output_file.read().strip()

    grammar = GrammarDriver(rules)
    i = Interpreter(grammar, input)
    output = i.run().strip()
    if output != expected_output:
      print("Got output:\n" + output)
      print("Wanted output:\n" + expected_output)
      exit(1)
    assert(output == expected_output)

  for input_file_name in bad_files:
    input_file_path = os.path.join(test_path, input_file_name)
    output_file_path = os.path.join(test_path, input_file_name[:-2] + "out")
    print("Running test " + input_file_path)
    if not os.path.isfile(output_file_path):
      print("Corresponding output file " + output_file_path + " not found")
      exit(1)
    input_file = open(input_file_path, 'r')
    input = input_file.read()
    if input.startswith("SKIP"):
      print("SKIPPED")
      skipped += 1
      continue
    output_file = open(output_file_path, 'r')
    expected_output = output_file.read().strip()

    grammar = GrammarDriver(rules)

    try:
      i = Interpreter(grammar, input)
      i.run()
    except BaseException as e:
      output = e.__class__.__name__
    else:
      print("Expecting an error, got none")
      exit(1)

    if output != expected_output:
      print("Got output:\n" + output)
      print("Wanted output:\n" + expected_output)
      exit(1)
    assert(output == expected_output)

  return skipped


if __name__ == '__main__':
  skipped = run_tests_in("interpreter_tests")
  skipped += run_tests_in("tests")

  if skipped > 0:
    print("Some tests skipped")
    exit(1)

  print("All OK!")
  exit(0)
