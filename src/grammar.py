#!/usr/bin/python3

from collections import defaultdict
from util import list_to_string, print_debug

class SyntaxError(BaseException):
  def __init__(self, pos = None, message = None):
    self.pos = pos
    self.message = message
  def __str__(self):
    return "SyntaxError: " + str(self.message) + " (" + str(self.pos) + ")"


class GrammarRule:
  def __init__(self, left, right, gatherer):
    self.left = left
    self.right = right
    self.gatherer = gatherer

  def __str__(self):
    return self.left + " -> " + list_to_string(self.right)


class GrammarDriver:
  def __init__(self, rules):
    self.rules = defaultdict(list)

    nonfinals = set()
    finals = set()
    for rule in rules:
      self.rules[rule.left].append((rule.right, rule))
      nonfinals.add(rule.left)
      for item in rule.right:
        if GrammarDriver.__isToken(item):
          finals.add(item)

    self.nonfinals = list(nonfinals)
    self.finals = list(finals)

    # print ("nonfinals" + str(self.nonfinals))
    # print ("finals" + str(self.finals))

    self.canBeEpsilon = defaultdict(bool)
    for nf in self.nonfinals:
      if self.__hasEpsilonRule(nf):
        self.canBeEpsilon[nf] = True
    self.canBeEpsilon["epsilon"] = True

    self.first = defaultdict(set)
    self.follow = defaultdict(set)

    for f in self.finals:
      self.first[f].add(f)

    # Compute FIRST and EPS
    didSomething = True
    while didSomething:
      didSomething = False
      for item in self.rules:
        productions = self.rules[item]
        for (production, rule) in productions:
          # print("handling " + str(item) + " -> " + str(production))
          if production[0] == "epsilon":
            continue
          # A -> B C, first(B) subset_of first(A)
          if GrammarDriver.__addSetToSet(self.first[item], self.first[production[0]]):
            # print("A -> B C, first(B) subset_of first(A)")
            # print("first of " + str(item) + " += " + str(self.first[production[0]]))
            didSomething = True

          # A -> B1 B2 .. Bn C, if all B's can be epsilon, first(C) subset_of first(A)
          firstDefNonEpsilon = None
          for rhsItem in production:
            if not self.canBeEpsilon[rhsItem]:
              firstDefNonEpsilon = rhsItem
              break
          if firstDefNonEpsilon:
            if GrammarDriver.__addSetToSet(self.first[item], self.first[firstDefNonEpsilon]):
              didSomething = True
          else:
            if not self.canBeEpsilon[item]:
              self.canBeEpsilon[item] = True
              didSomething = True


    # Compute FOLLOW
    didSomething = True
    while didSomething:
      didSomething = False
      for item in self.rules:
        productions = self.rules[item]
        for (production, rule) in productions:
          #print("Processing: " + str(item) + " -> " + str(production))
          # A -> B C D, first(C) subset_of follow(B), and first(D) subset_of follow(C)
          for i in range(len(production) - 1):
            whatToAdd = i + 1
            while whatToAdd < len(production):
              if GrammarDriver.__addSetToSet(self.follow[production[i]],
                                             self.first[production[whatToAdd]]):
                didSomething = True
              # If C can be epsilon, then first(D) subset_of follow(B)
              if self.canBeEpsilon[production[whatToAdd]]:
                whatToAdd += 1
              else:
                break

          # A -> B C D, follow(A) subset_of follow(D)
          for i in reversed(range(len(production))):
            if GrammarDriver.__addSetToSet(self.follow[production[i]], self.follow[item]):
              didSomething = True
            # If D can be epsilon, then follow(A) subset_of follow(C)
            if not self.canBeEpsilon[production[i]]:
              break

    # Compute PREDICT
    self.predictions = defaultdict(defaultdict)
    self.success = True

    for item in self.rules:
      productions = self.rules[item]
      for (production, rule) in productions:
        predictSet = set()
        # print_debug("Processing: " + str(item) + " -> " + str(production))

        # A -> B C, predict to use this rule if the symbol in first(B) or if B can be epsilon and the symbol in first(C), or if all can be epsilon and symbol in follow(A).
        for i in range(len(production)):
          # print_debug("Case 1: adding to predictSet: " + str(self.first[production[i]]))
          GrammarDriver.__addSetToSet(predictSet, self.first[production[i]])
          if not self.canBeEpsilon[production[i]]:
            break
          if i < len(production) - 1:
            # print_debug("Case 2: adding to predictSet: " + str(self.first[production[i]]))
            GrammarDriver.__addSetToSet(predictSet, self.first[production[i + 1]])
          else: # all can be epsilon
            # print_debug("Case 3: adding to predictSet: " + str(self.first[production[i]]))
            GrammarDriver.__addSetToSet(predictSet, self.follow[item])
        for f in predictSet:
          if f in self.predictions[item]:
            print_debug("Going to fail; rule " + str(item) + " -> " + str(production))
            print_debug("Already in predictions[" + str(item) + "]: " + str(f))
            self.success = False
            assert(False)
          # print_debug("Adding: predictions[" + str(item) + "][" + str(f) + "]")
          self.predictions[item][f] = (production, rule)

    # print_debug("first:")
    # for item in self.first:
    #   print_debug(str(item) + " -> " + str(self.first[item]))

    # print_debug("follow:")
    # for item in self.follow:
    #   print_debug(str(item) + " -> " + str(self.follow[item]))

    # print_debug("predict:")
    # for item in self.predictions:
    #   for f in self.predictions[item]:
    #     print_debug("(" + str(item) + ", " + str(f) + ") -> " + str(self.predictions[item][f]))

    assert(self.success)
    # print("success: " + str(self.success))

  def predict(self, top_of_stack, token):
    if top_of_stack not in self.predictions or token not in self.predictions[top_of_stack]:
      raise SyntaxError(None, "Grammar error: top of stack is " + str(top_of_stack) + ", token is: " + str(token))
    return self.predictions[top_of_stack][token]

  @staticmethod
  def __isToken(item):
    return item.find("token_") == 0

  def __hasEpsilonRule(self, item):
    for (rhs, rule) in self.rules[item]:
      if rhs == ["epsilon"]:
        return True
    return False

  @staticmethod
  def __addToSet(s, item):
    if item in s:
      return False
    s.add(item)
    return True

  def __addSetToSet(s1, s2):
    added_something = False
    for item in s2:
      if not item in s1:
        added_something = True
      s1.add(item)
    return added_something
