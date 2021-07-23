from me2.bits import *
import unittest

class FfsTest(unittest.TestCase):
  def test_ffs_one_bit(self):
    self.assertEqual(ffs(0x2000), 13)

  def test_ffs_multiple_bits(self):
    self.assertEqual(ffs(42), 1)

  def test_ffs_zero_bits(self):
    self.assertEqual(ffs(0), -1)

class LsbTest(unittest.TestCase):
  def test_lsb_one_bit(self):
    self.assertEqual(lsb(64), 64)

  def test_lsb_multiple_bits(self):
    self.assertEqual(lsb(0xf00db8), 8)

  def test_lsb_zero_bits(self):
    self.assertEqual(lsb(0), 0)

class MaskTest(unittest.TestCase):
  def test_positive(self):
    self.assertEqual(mask(4), 15)

  def test_zero(self):
    self.assertEqual(mask(0), 0)

  def test_negative(self):
    with self.assertRaises(ValueError):
      mask(-1)


if __name__ == '__main__':
  unittest.main()