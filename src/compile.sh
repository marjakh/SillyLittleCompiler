#!/bin/bash

BASEDIR=$(dirname "$0")
python3 $BASEDIR/compiler.py $1 > /tmp/temp.as && as -32 -ggstabs -o /tmp/temp.o /tmp/temp.as && make -C $BASEDIR/../runtime && g++ -m32 /tmp/temp.o $BASEDIR/../runtime/runtime.o $BASEDIR/../runtime/builtins.o $BASEDIR/../runtime/memory.o $BASEDIR/../runtime/stack_walk.o -o /tmp/a.out
