This is a silly little compiler.

(c) Marja Hölttä (a proper license will follow)

Purpose
==============

To study programming language / compiler concepts.
- Rule-based parsing
- Register allocation
- Assembly
- Optimizations (TODO)


The language
==============

The language is a self invented one which might or might not resemble
JavaScript.

- Functions + inner functions
- Garbage collected (garbage collection not implemented)


Status of the silly little compiler
==============

At the moment, the silly little compiler can only compile simple and small
programs.

- The only datatype is int
- GC not impelemented yet

The interpreter is more complete and can run all programs in tests/.


Requirements
==============
sudo apt-get install gcc-multilib g++-multilib
