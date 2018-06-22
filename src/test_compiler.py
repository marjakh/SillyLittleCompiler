#!/usr/bin/python3

from grammar import GrammarDriver
from grammar_rules import rules
from interpreter import Interpreter

from enum import Enum
import os
import re
import subprocess


class TestResultStatus(Enum):
  error = 1
  ok = 2
  skipped = 3

class Result:
  def __init__(self, status, output = None, longer_output = None):
    self.status = status
    self.output = output
    self.longer_output = longer_output

  @staticmethod
  def testSkipped():
    return Result(TestResultStatus.skipped)

  @staticmethod
  def testOk(output):
    return Result(TestResultStatus.ok, output)

  @staticmethod
  def testError(output, longer_output):
    return Result(TestResultStatus.error, output, longer_output)


def getOutput(input_file_name, gc_stress):
  print("Running test " + input_file_name + ", gc_stress " + str(gc_stress))

  input_file_path = os.path.join(test_path, input_file_name)
  input_file = open(input_file_path, 'r')
  input = input_file.read()
  if input.startswith("SKIP"):
    print("SKIPPED")
    return Result.testSkipped()

  input_file.close()

  output = ""
  try:
    compile_output = subprocess.check_output(["src/compile.sh", input_file_path], stderr = subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    error_line = e.output.decode("utf-8").split('\n')[-2]
    error_search = re.search("(.*?)\.(.*?):", error_line)
    if error_search:
      output = error_search.group(2)
    return Result.testError(output, error_line)

  command = ["/tmp/a.out"]
  if gc_stress:
    command = command + ["--gc-stress"]
  output = subprocess.check_output(command).decode("utf-8").strip()
  return Result.testOk(output)

skipped = 0

def runTest(input_file_name, test_path, expect_error, gc_stress):
  global skipped

  result = getOutput(input_file_name, gc_stress)

  output_file_name = input_file_name[:-2] + "out"
  if not os.path.isfile(os.path.join(test_path, output_file_name)):
    print("Corresponding output file " + output_file_name + " not found")
    exit(1)

  output_file = open(os.path.join(test_path, output_file_name), 'r')
  expected_output = output_file.read().strip()
  output_file.close()

  if result.status == TestResultStatus.skipped:
    skipped += 1
    return

  if expect_error == False and result.status == TestResultStatus.error:
    print("Expected no error, got error:\n" + result.longer_output)
    exit(1)

  if expect_error == True and result.status == TestResultStatus.ok:
    print("Expected error, got none")
    exit(1)

  if result.output != expected_output:
    print("Got output:\n" + result.output)
    print("Wanted output:\n" + expected_output)
    exit(1)
  assert(result.output == expected_output)



if __name__ == '__main__':

  # Read all input files in tests/, run the prog with the compiler, ensure
  # that the output matches the corresponding output file.
  test_paths = ["tests", "compiler_tests"]

  for test_path in test_paths:
    files = [f for f in os.listdir(test_path) if os.path.isfile(os.path.join(test_path, f)) and f.endswith("in")]

    good_files = [f for f in files if not f.startswith("error_")]
    good_files.sort()
    bad_files = [f for f in files if f.startswith("error_")]
    bad_files.sort()

    for input_file_name in good_files:
      runTest(input_file_name, test_path, False, False)

    for input_file_name in bad_files:
      runTest(input_file_name, test_path, True, False)

    for input_file_name in good_files:
      runTest(input_file_name, test_path, False, True)

    for input_file_name in bad_files:
      runTest(input_file_name, test_path, True, True)

    if skipped > 0:
      print("Some tests skipped")
      exit(1)

  print("All OK!")
  exit(0)
