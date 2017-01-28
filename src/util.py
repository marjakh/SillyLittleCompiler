import sys

def listToString(lst, begin="[", end="]", delimiter=", "):
  if lst == None:
    return begin+end
  s = begin
  for (n, i) in enumerate(lst):
    if n > 0:
      s += delimiter
    if isinstance(i, list):
      s += listToString(i)
    else:
      s += str(i)
  s += end
  return s

def dictToString(d, begin="{", end="}"):
  s = begin
  first = True
  for key, value in d.items():
    if not first:
      s += ", "
    first = False
    s += (toString(key) + ": " + toString(value))
  s += end
  return s

def toString(sth):
  if isinstance(sth, list):
    return listToString(sth)
  if isinstance(sth, dict):
    return dictToString(sth)
  if isinstance(sth, set):
    return listToString(list(sth), "{", "}")
  return str(sth)

def print_error(msg):
  print(msg, file=sys.stderr)

def print_debug(msg):
  print(msg, file=sys.stderr)
