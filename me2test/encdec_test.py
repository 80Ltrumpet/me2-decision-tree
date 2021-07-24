from me2.ally import Ally
from me2.encdec import Decoder, Encoder, decode_outcome, encode_outcome
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
    self.encoder.encode_ally(Ally.Garrus)
    self.encoder.encode_ally(Ally.Tali)
    self.assertEqual(self.encoder.result, 0x400001)

  def test_encode_ally_loyalty(self):
    self.encoder.encode_ally_loyalty(Ally.Thane | Ally.Zaeed)
    self.encoder.encode_ally_loyalty(Ally.Jacob | Ally.Jack)
    self.assertEqual(self.encoder.result, 0x006c00)

  def test_encode_ally_optional(self):
    self.encoder.encode_ally_optional(Ally.Grunt | Ally.Mordin)
    self.encoder.encode_ally_optional(Ally.Legion | Ally.Kasumi)
    self.assertEqual(self.encoder.result, 0x601)

  def test_encode_ally_index(self):
    self.encoder.encode_ally_index(Ally.Samara)
    self.encoder.encode_ally_index(Ally.Miranda)
    self.assertEqual(self.encoder.result, 0x49)

  def test_encode_squad(self):
    self.encoder.encode_squad(Ally.Garrus | Ally.Tali)
    self.encoder.encode_squad(Ally.Morinth | Ally.Jack)
    self.assertEqual(self.encoder.result, 0xd2a1)

  def test_encode_choices(self):
    self.encoder.encode_choices([])
    self.encoder.encode_choices([Ally.Jacob])
    self.encoder.encode_choices([Ally.Kasumi, Ally.Mordin])
    self.encoder.encode_choices([Ally.Thane, Ally.Miranda, Ally.Zaeed])
    self.assertEqual(self.encoder.result, 0x4b2bc0e01)


class OutcomeEncoderTest(unittest.TestCase):
  def test_result(self):
    # This isn't exactly a valid outcome, but that doesn't matter for encoding!
    encoded_outcome = encode_outcome(
      spared = Ally.Jacob | Ally.Grunt | Ally.Thane,
      dead = Ally.Zaeed | Ally.Legion,
      loyalty = Ally.Grunt | Ally.Jacob,
      crew = True
    )
    self.assertEqual(encoded_outcome, 0x204888424)


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
    self.assertEqual(decoder.decode_squad(), Ally.Miranda | Ally.Grunt)
    self.assertEqual(decoder.decode_squad(), Ally.Morinth | Ally.Jacob)

  def test_decode_choices(self):
    decoder = Decoder(0x3640f)
    self.assertEqual(decoder.decode_choices(), (True, [Ally.Kasumi]))
    self.assertEqual(decoder.decode_choices(),
                     (False, [Ally.Samara, Ally.Morinth]))


class OutcomeDecoderTest(unittest.TestCase):
  def test_result(self):
    self.assertEqual(decode_outcome(0x2094020cb),
      {
        'spared': Ally.Garrus | Ally.Jack | Ally.Kasumi | Ally.Legion | \
                  Ally.Miranda,
        'dead': Ally.Grunt | Ally.Jacob | Ally.Mordin,
        'loyalty': Ally.Jack | Ally.Kasumi | Ally.Miranda,
        'crew': True
      }
    )


if __name__ == '__main__':
  unittest.main()