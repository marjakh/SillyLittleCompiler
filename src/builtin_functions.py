#!/usr/bin/python3

def addBuiltinFunctionShapes(function_param_counts, function_local_counts):
  function_param_counts["write"] = 1 # FIXME: define this constant somewhere
  function_param_counts["Array"] = 1 # FIXME: define this constant somewhere
  function_param_counts["test_do_gc"] = 0
  function_param_counts["test_is_live_object"] = 1

  function_local_counts["write"] = 0
  function_local_counts["Array"] = 0
  function_local_counts["test_do_gc"] = 0
  function_local_counts["test_is_live_object"] = 0
  # TODO: expand
