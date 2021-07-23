from __future__ import annotations

class Bits(int):
  """Integer with a user-defined bit length"""
  def __new__(cls, value: int, length: int) -> Bits:
    """Creates a new Bits object with the given value and length."""
    return super(Bits, cls).__new__(cls, value & ((1 << length) - 1))

  def __init__(self, value: int, length: int) -> None:
    """Initializes the bit length of this Bits instance."""
    self.length = length

  def bit_length(self) -> int:
    """Custom override of int's bit_length() method."""
    return self.length


def ffs(x: int) -> int:
  """Finds the position of the first set bit in x or -1 if no bits are set."""
  bit = 0
  mask = 1
  while mask <= x:
    if mask & x:
      return bit
    bit += 1
    mask <<= 1
  return -1

def lsb(x: int) -> int:
  """Returns the value of the first set bit in x or 0 if no bits are set."""
  mask = 1
  while mask <= x:
    if mask & x:
      return mask
    mask <<= 1
  return 0