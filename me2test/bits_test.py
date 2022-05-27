#
# Copyright (c) 2022 Andrew Lehmer
#
# Distributed under the MIT License.
#

from me2.bits import *
import unittest

class BitsTest(unittest.TestCase):
  def test_has_bits(self):
    self.assertEqual(list(bits(42)), [2, 8, 32])

  def test_no_bits(self):
    self.assertEqual(list(bits(0)), [])

class BitIndicesTest(unittest.TestCase):
  def test_has_bits(self):
    self.assertEqual(list(bit_indices(0x69)), [0, 3, 5, 6])

  def test_no_bits(self):
    self.assertEqual(list(bit_indices(0)), [])

class FfsTest(unittest.TestCase):
  def test_ffs_one_bit(self):
    self.assertEqual(ffs(0x2000), 13)

  def test_ffs_multiple_bits(self):
    self.assertEqual(ffs(42), 1)

  def test_ffs_zero_bits(self):
    self.assertEqual(ffs(0), -1)

class FsbTest(unittest.TestCase):
  def test_fsb_one_bit(self):
    self.assertEqual(fsb(64), 64)

  def test_fsb_multiple_bits(self):
    self.assertEqual(fsb(0xf00db8), 8)

  def test_fsb_zero_bits(self):
    self.assertEqual(fsb(0), 0)

class MaskTest(unittest.TestCase):
  def test_positive(self):
    self.assertEqual(mask(4), 15)

  def test_zero(self):
    self.assertEqual(mask(0), 0)

  def test_negative(self):
    with self.assertRaises(ValueError):
      mask(-1)

class MtzTest(unittest.TestCase):
  def test_positive(self):
    self.assertEqual(mtz(0xb00), 0xff)

  def test_zero(self):
    self.assertEqual(mtz(0), 0)

class PopcountTest(unittest.TestCase):
  def test_positive(self):
    self.assertEqual(popcount(0xdead), 11)
    self.assertEqual(popcount(0x123456), 9)

  def test_zero(self):
    self.assertEqual(popcount(0), 0)


if __name__ == "__main__":
  unittest.main()