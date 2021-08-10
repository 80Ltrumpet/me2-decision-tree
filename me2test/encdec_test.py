from me2.ally import Ally
from me2.bits import ffs
from me2.encdec import DecodedOutcome, Decoder, Encoder, decode_outcome, encode_outcome
import unittest

class EncoderTest(unittest.TestCase):
  def setUp(self) -> None:
    # Each test gets a fresh encoder.
    self.encoder = Encoder()

  def test_encode_bool(self):
    self.encoder.encode_bool(False)
    self.encoder.encode_bool(True)
    self.assertEqual(self.encoder.result, 2)

  def test_encode_ally(self):
    self.encoder.encode_ally(Ally.Garrus.value)
    self.encoder.encode_ally(Ally.Tali.value)
    self.assertEqual(self.encoder.result, 0x400001)

  def test_encode_ally_loyalty(self):
    self.encoder.encode_ally_loyalty((Ally.Thane | Ally.Zaeed).value)
    self.encoder.encode_ally_loyalty((Ally.Jacob | Ally.Jack).value)
    self.assertEqual(self.encoder.result, 0x00ac00)

  def test_encode_ally_optional(self):
    self.encoder.encode_ally_optional((Ally.Grunt | Ally.Mordin).value)
    self.encoder.encode_ally_optional((Ally.Legion | Ally.Kasumi).value)
    self.assertEqual(self.encoder.result, 0x601)

  def test_encode_ally_index(self):
    self.encoder.encode_ally_index(ffs(Ally.Samara.value, 1))
    self.encoder.encode_ally_index(ffs(Ally.Miranda.value, 1))
    self.assertEqual(self.encoder.result, 0x39)

  def test_encode_squad(self):
    self.encoder.encode_squad((Ally.Garrus | Ally.Tali).value)
    self.encoder.encode_squad((Ally.Morinth | Ally.Jack).value)
    self.assertEqual(self.encoder.result, 0xd4a1)

  def test_encode_choices(self):
    self.encoder.encode_choices([])
    self.encoder.encode_choices([Ally.Jacob.value])
    self.encoder.encode_choices([Ally.Kasumi.value, Ally.Mordin.value])
    self.encoder.encode_choices([Ally.Thane.value,
                                 Ally.Miranda.value,
                                 Ally.Zaeed.value])
    self.assertEqual(self.encoder.result, 0x3b2bc0a01)


class OutcomeEncoderTest(unittest.TestCase):
  def test_result(self):
    # This isn't exactly a valid outcome, but that doesn't matter for encoding!
    encoded_outcome = encode_outcome(
      spared = (Ally.Jacob | Ally.Grunt | Ally.Thane).value,
      loyalty = (Ally.Grunt | Ally.Jacob).value,
      crew = True
    )
    self.assertEqual(encoded_outcome, 0x2044422)


class DecoderTest(unittest.TestCase):
  def test_decode_bool(self):
    decoder = Decoder(2)
    self.assertFalse(decoder.decode_bool())
    self.assertTrue(decoder.decode_bool())

  def test_decode_ally(self):
    decoder = Decoder(0x23ba98c)
    self.assertEqual(decoder.decode_ally(), Ally(0x98c))
    self.assertEqual(decoder.decode_ally(), Ally(0x11dd))

  def test_decode_ally_loyalty(self):
    decoder = Decoder(0x123456)
    self.assertEqual(decoder.decode_ally_loyalty(), Ally(0x456))
    self.assertEqual(decoder.decode_ally_loyalty(), Ally(0x123))

  def test_decode_ally_optional(self):
    decoder = Decoder(0xbeef)
    self.assertEqual(decoder.decode_ally_optional(), Ally(0x1de0))
    self.assertEqual(decoder.decode_ally_optional(), Ally(0x17c0))

  def test_decode_ally_index(self):
    decoder = Decoder(0xa1)
    self.assertEqual(decoder.decode_ally_index(), Ally.Garrus)
    self.assertEqual(decoder.decode_ally_index(), Ally.Tali)

  def test_decode_squad(self):
    decoder = Decoder(0xd346)
    self.assertEqual(decoder.decode_squad(), Ally.Jack | Ally.Grunt)
    self.assertEqual(decoder.decode_squad(), Ally.Morinth | Ally.Miranda)

  def test_decode_choices(self):
    decoder = Decoder(0x3640f)
    self.assertEqual(decoder.decode_choices(), (True, [Ally.Kasumi]))
    self.assertEqual(decoder.decode_choices(),
                     (False, [Ally.Samara, Ally.Morinth]))


class OutcomeDecoderTest(unittest.TestCase):
  def test_result(self):
    self.assertEqual(decode_outcome(0x20940cb),
      DecodedOutcome(
        spared = (Ally.Garrus | Ally.Jacob | Ally.Jack | Ally.Kasumi |
                  Ally.Legion),
        loyalty = Ally.Jacob | Ally.Jack | Ally.Kasumi,
        crew = True
      )
    )


if __name__ == '__main__':
  unittest.main()