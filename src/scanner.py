#!/usr/bin/python3

from enum import Enum

class TokenType(Enum):
  invalid = 0
  number = 1
  string = 2
  identifier = 3
  plus = 4
  minus = 5
  multiplication = 6
  division = 7
  equals = 8
  not_equals = 9
  less_than = 10
  less_or_equals = 11
  greater_than = 12
  greater_or_equals = 13
  left_paren = 14
  right_paren = 15
  left_curly = 16
  right_curly = 17
  left_bracket = 18
  right_bracket = 19
  assign = 20
  colon = 21
  semicolon = 22
  dot = 23
  comma = 24
  arrow = 25
  keyword_if = 26
  keyword_else = 27
  keyword_while = 28
  keyword_let = 29
  keyword_function = 30
  keyword_return = 31
  keyword_new = 32
  eos = 33


class Token:
  def __init__(self, token_type, value = None):
    self.token_type = token_type
    self.value = value

  def __str__(self):
    s = "Token(" + str(self.token_type)
    if self.value:
      s += ", " + str(self.value)
    s += ")"
    return s

  # The name of the token which occurs in the grammar
  def name(self):
    s = str(self.token_type) # TokenType.name
    return "token_" + s.split(".")[1]


class StringTable:
  def __init__(self):
    self.__strings = dict()
    self.__strings_array = []

  def addString(self, s):
    if s not in self.__strings:
      ix = len(self.__strings)
      self.__strings[s] = ix
      self.__strings_array.append(s)

  def indexOfString(self, s):
    return self.__strings[s]

  def dump(self):
    main_string = ""
    for s in self.__strings_array:
      main_string += s + "\\0"
    return "\"" + main_string + "\""

  def stringCount(self):
    return len(self.__strings_array)

class Scanner:
  # Order matters.
  __trivialTokens = [
    ("==", TokenType.equals),
    ("!=", TokenType.not_equals),
    ("<=", TokenType.less_or_equals),
    (">=", TokenType.greater_or_equals),
    ("->", TokenType.arrow),
    ("+", TokenType.plus),
    ("-", TokenType.minus),
    ("*", TokenType.multiplication),
    ("/", TokenType.division),
    ("(", TokenType.left_paren),
    (")", TokenType.right_paren),
    ("{", TokenType.left_curly),
    ("}", TokenType.right_curly),
    ("[", TokenType.left_bracket),
    ("]", TokenType.right_bracket),
    ("=", TokenType.assign),
    ("<", TokenType.less_than),
    (">", TokenType.greater_than),
    (":", TokenType.colon),
    (";", TokenType.semicolon),
    (".", TokenType.dot),
    (",", TokenType.comma),
  ]

  __keywords = {
    "if": TokenType.keyword_if,
    "else": TokenType.keyword_else,
    "while": TokenType.keyword_while,
    "let": TokenType.keyword_let,
    "function": TokenType.keyword_function,
    "return": TokenType.keyword_return,
    "new": TokenType.keyword_new,
  }

  @staticmethod
  def tokenNameToString(name):
    wanted_type = eval("TokenType." + name[len("token_"):])
    for (token_string, token_type) in Scanner.__trivialTokens:
      if token_type == wanted_type:
        return token_string
    assert(False)

  def __init__(self, s):
    self.s = s
    self.pos = 0
    self.__skipWhitespaceAndComments()
    self.string_table = StringTable()

  def __skipWhitespaceAndComments(self):
    self.__skipWhitespace()
    while self.pos + 1 < len(self.s) and self.s[self.pos] == "/" and self.s[self.pos + 1] == "/":
      self.pos += 2
      self.__skipUntilNewline()
      self.__skipWhitespace()

  def __skipWhitespace(self):
    while self.__hasMore() and (self.s[self.pos] == " " or self.s[self.pos] == "\n"):
      self.pos += 1

  def __skipUntilNewline(self):
    while self.__hasMore() and self.s[self.pos] != "\n":
      self.pos += 1

  def __scanNumber(self):
    n = 0
    while self.__hasMore() and self.s[self.pos] >= "0" and self.s[self.pos] <= "9":
      n = n * 10 + ord(self.s[self.pos]) - ord("0")
      self.pos += 1
    return Token(TokenType.number, n)

  def __scanString(self):
    self.pos += 1
    s = ""
    while self.__hasMore() and self.s[self.pos] != "\"":
      # FIXME: escaping
      s += self.s[self.pos]
      self.pos += 1
    self.pos += 1
    self.string_table.addString(s)
    return Token(TokenType.string, s)

  def __scanIdentifierOrKeyword(self):
    name = ""
    while self.__hasMore() and (
        (self.s[self.pos] >= "a" and self.s[self.pos] <= "z") or
        (self.s[self.pos] >= "A" and self.s[self.pos] <= "Z") or
        (self.s[self.pos] >= "0" and self.s[self.pos] <= "9") or
        self.s[self.pos] == '_'):
      name += self.s[self.pos]
      self.pos += 1
    if name in Scanner.__keywords:
      return Token(Scanner.__keywords[name])
    return Token(TokenType.identifier, name)

  def __hasMore(self):
    return self.pos < len(self.s)

  def nextToken(self):
    token = self.__readNextToken()
    self.__skipWhitespaceAndComments()
    return token

  def __readNextToken(self):
    if not self.__hasMore():
      return Token(TokenType.eos)

    c = self.s[self.pos]

    for (token_string, token_type) in Scanner.__trivialTokens:
      if len(self.s[self.pos:]) >= len(token_string) and self.s[self.pos:(self.pos + len(token_string))] == token_string:
        self.pos += len(token_string)
        return Token(token_type)

    if self.s[self.pos] >= "0" and self.s[self.pos] <= "9":
      return self.__scanNumber()
    if ((self.s[self.pos] >= "a" and self.s[self.pos] <= "z") or
        (self.s[self.pos] >= "A" and self.s[self.pos] <= "Z")):
      return self.__scanIdentifierOrKeyword()
    if self.s[self.pos] == "\"":
      return self.__scanString()

    return Token(TokenType.invalid)
