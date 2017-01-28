
class Super:
  def __init__(self):
    pass

  def foo(self):
    print("Superfoo with " + str(self))

class Sub(Super):
  def __init__(self):
    super(Sub, self).__init__()

  def foo(self):
    print("Subfoo with " + str(self))
    # super(Sub, self).foo()

    f = Sub()
    print("new object is " + str(f))
    super(Sub, f).foo()


if __name__ == "__main__":
  s = Sub()
  s.foo()

