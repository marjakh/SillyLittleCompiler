#!/usr/bin/python3

from enum import Enum

class TokenType(Enum):
  invalid = 0
  number = 1
  identifier = 2
  plus = 3
  minus = 4
  multiplication = 5
  division = 6
  equals = 7
  not_equals = 8
  less_than = 9
  less_or_equals = 10
  greater_than = 11
  greater_or_equals = 12
  left_paren = 13
  right_paren = 14
  left_curly = 15
  right_curly = 16
  assign = 17
  semicolon = 18
  comma = 19
  keyword_if = 20
  keyword_else = 21
  keyword_while = 22
  keyword_let = 23
  keyword_function = 24
  keyword_return = 25
  eos = 26


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


class Scanner:
  # Order matters.
  __trivialTokens = [
    ("==", TokenType.equals),
    ("!=", TokenType.not_equals),
    ("<=", TokenType.less_or_equals),
    (">=", TokenType.greater_or_equals),
    ("+", TokenType.plus),
    ("-", TokenType.minus),
    ("*", TokenType.multiplication),
    ("/", TokenType.division),
    ("(", TokenType.left_paren),
    (")", TokenType.right_paren),
    ("{", TokenType.left_curly),
    ("}", TokenType.right_curly),
    ("=", TokenType.assign),
    ("<", TokenType.less_than),
    (">", TokenType.greater_than),
    (";", TokenType.semicolon),
    (",", TokenType.comma),
  ]

  __keywords = {
    "if": TokenType.keyword_if,
    "else": TokenType.keyword_else,
    "while": TokenType.keyword_while,
    "let": TokenType.keyword_let,
    "function": TokenType.keyword_function,
    "return": TokenType.keyword_return,
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

  def __scanIdentifierOrKeyword(self):
    name = ""
    while self.__hasMore() and (
        (self.s[self.pos] >= "a" and self.s[self.pos] <= "z") or
        (self.s[self.pos] >= "0" and self.s[self.pos] <= "9")):
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
    if self.s[self.pos] >= "a" and self.s[self.pos] <= "z":
      return self.__scanIdentifierOrKeyword()

    return Token(TokenType.invalid)

if __name__ == "__main__":
  s = Scanner("foo 133 + / - *    bar baz")
  for i in range(1, 10):
    print(s.nextToken())
