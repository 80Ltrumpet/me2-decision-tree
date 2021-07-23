from __future__ import annotations

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

def mask(length: int) -> int:
  """Returns a bit mask with length LSBs set."""
  return (1 << length) - 1