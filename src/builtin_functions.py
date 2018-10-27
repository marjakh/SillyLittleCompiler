#!/usr/bin/python3

def addBuiltinFunctionShapes(function_param_and_local_counts):
  function_param_and_local_counts["print"] = 1 # FIXME: define this constant somewhere
  function_param_and_local_counts["Array"] = 1 # FIXME: define this constant somewhere
  function_param_and_local_counts["test_do_gc"] = 0
  function_param_and_local_counts["test_is_live_object"] = 1

  # TODO: expand
