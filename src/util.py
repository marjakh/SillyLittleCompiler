import sys

def list_to_string(lst, begin="[", end="]", delimiter=", "):
  if lst == None:
    return begin+end
  s = begin
  for (n, i) in enumerate(lst):
    if n > 0:
      s += delimiter
    if isinstance(i, list):
      s += list_to_string(i)
    else:
      s += str(i)
  s += end
  return s

def dict_to_string(d, begin="{", end="}"):
  s = begin
  first = True
  for key, value in d.items():
    if not first:
      s += ", "
    first = False
    s += (to_string(key) + ": " + to_string(value))
  s += end
  return s

def to_string(sth):
  if isinstance(sth, list):
    return list_to_string(sth)
  if isinstance(sth, dict):
    return dict_to_string(sth)
  if isinstance(sth, set):
    return list_to_string(list(sth), "{", "}")
  return str(sth)

def print_error(msg):
  print(msg, file=sys.stderr)

def print_debug(msg):
  print(msg, file=sys.stderr)
