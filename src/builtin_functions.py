#!/usr/bin/python3

def addBuiltinFunctionShapes(function_context_shapes):
  function_context_shapes["write"] = 1 # FIXME: define this constant somewhere
  function_context_shapes["Array"] = 1 # FIXME: define this constant somewhere
  function_context_shapes["test_do_gc"] = 0
  function_context_shapes["test_is_live_object"] = 1
  # TODO: expand
