#
# Copyright (c) 2022 Andrew Lehmer
#
# Distributed under the MIT License.
#

from __future__ import annotations
from collections.abc import Generator
from typing import Literal

IntGenerator = Generator[int, None, None]

def bits(x: int) -> IntGenerator:
  """Generates an int with one bit set for each bit set in x.
  
  >>> list(bits(42))
  [2, 8, 32]
  >>> [hex(bit) for bit in bits(0xbad)]
  ['0x1', '0x4', '0x8', '0x20', '0x80', '0x100', '0x200', '0x800']
  """
  mask = 1
  while mask <= x:
    if mask & x:
      yield mask
    mask <<= 1

def bit_indices(x: int, start: Literal[0, 1] = 0) -> IntGenerator:
  """Generates the bit index for each set bit in x where the index of the LSB
  is start.
  
  >>> list(bit_indices(42))
  [1, 3, 5]
  >>> list(bit_indices(0x69, 1))
  [1, 4, 6, 7]
  """
  index = start
  mask = 1
  while mask <= x:
    if mask & x:
      yield index
    index += 1
    mask <<= 1

def ffs(x: int) -> int:
  """Finds the position of the first set bit in x or -1 if no bits are set.
  
  >>> ffs(42)
  1
  >>> ffs(0xb00)
  8
  """
  bit = 0
  mask = 1
  while mask <= x:
    if mask & x:
      return bit
    bit += 1
    mask <<= 1
  return -1

def fsb(x: int) -> int:
  """Returns the value of the first set bit in x or 0 if no bits are set.
  
  >>> fsb(42)
  2
  >>> fsb(0x88)
  8
  """
  mask = 1
  while mask <= x:
    if mask & x:
      return mask
    mask <<= 1
  return 0

def mask(length: int) -> int:
  """Returns a bit mask with length LSBs set.
  
  >>> mask(5)
  31
  """
  return (1 << length) - 1

def mtz(x: int) -> int:
  """Returns a mask of the trailing zero bits in x.
  
  >>> mtz(0x38)
  7
  >>> mtz(1)
  0
  """
  return fsb(x) - 1 if x else 0

def popcount(x: int) -> int:
  """Returns the number of set bits in x.
  
  >>> popcount(0b1101111010101101)
  11
  """
  return bin(x).count('1')