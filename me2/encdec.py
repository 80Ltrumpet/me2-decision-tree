from typing import Any, Union

from .bits import Bits, ffs as _ffs
from .defs import Ally, LOYALTY_MASK, NOBODY, OPTIONAL, REQUIRED

_ALLY_LEN = len(Ally)
_ALLY_LOYALTY_LEN = len(LOYALTY_MASK)
_ALLY_OPTIONAL_LEN = len(OPTIONAL)
_ALLY_OPTIONAL_SHIFT = _ffs(OPTIONAL.value)
_ALLY_INDEX_LEN = _ALLY_LEN.bit_length()

class Encoder:
  """Facilitates bit-packing various types in a variable sequence."""
  def __init__(self) -> None:
    """Constructs a SequencedEncoder instance."""
    self._result = 0

  def _append(self, bits: int) -> None:
    bl = self._result.bit_length()
    self._result = Bits(self._result | bits << bl, bl + bits.bit_length())

  def get_result(self) -> int:
    """Returns the currently encoded result as an int."""
    return int(self._result)

  def encode_bool(self, value: bool) -> None:
    """Encodes a bool as a single bit."""
    self._append(Bits(value, 1))

  def encode_ally(self, ally: Ally) -> None:
    """Encodes an Ally's value.
    
    For Ally enumeration members, see encode_ally_index().
    """
    self._append(Bits(ally.value, _ALLY_LEN))

  def encode_ally_loyalty(self, loyalty: Ally) -> None:
    """Encodes an Ally's value masked by LOYALTY_MASK."""
    self._append(Bits(loyalty.value, _ALLY_LOYALTY_LEN))

  def encode_ally_optional(self, ally: Ally) -> None:
    """Encodes an Ally's value masked by OPTIONAL."""
    self._append(Bits((ally & OPTIONAL).value >> _ALLY_OPTIONAL_SHIFT,
                      _ALLY_OPTIONAL_LEN))

  def encode_ally_index(self, index: Union[Ally, int]) -> None:
    """Encodes an Ally's index starting from 1.

    This requires fewer bits than encode_ally().
    """
    if isinstance(index, Ally):
      index = index.index()
    self._append(Bits(index, _ALLY_INDEX_LEN))

  def encode_squad(self, squad: Ally) -> None:
    """Encodes two Ally indices based on the given squad.
    
    If squad does not contain exactly two set bits, raises a ValueError.
    """
    i = 0
    for i, index in enumerate(squad.indices()):
      if i >= 2:
        raise ValueError(f'Too many squadmates: {squad}')
      self.encode_ally_index(index)
    if i != 1:
      raise ValueError(f'Not a full squad: {squad}')

  def encode_choices(self, choices: list[Ally]) -> None:
    """Encodes two Ally indices with a preceding bit indicating whether the
    last non-zero index should be treated as an opposite choice.
    
    The semantics of this value and the phrase "opposite choice" are
    context-dependent.
    """
    first_choice = choices[0] if choices and choices[0] else NOBODY
    second_choice = choices[1] if first_choice and len(choices) > 1 else NOBODY
    self.encode_bool(len(choices) < 3)
    self.encode_ally_index(first_choice)
    self.encode_ally_index(second_choice)


def encode_outcome(**outcome) -> int:
  """Encodes outcome data as an int."""
  # The loyalty of dead allies does not affect the outcome.
  loyalty = outcome['spared'] & outcome['loyalty']
  encoder = Encoder()
  encoder.encode_ally(outcome['spared'])
  encoder.encode_ally_optional(outcome['dead'])
  encoder.encode_ally_loyalty(loyalty)
  encoder.encode_bool(outcome['crew'])
  return encoder.get_result()


class Decoder:
  """Decodes a bit-packed value with a potentially variable sequence."""
  def __init__(self, encoded: int) -> None:
    self.encoded = encoded

  def _shift(self, length: int) -> int:
    bits = Bits(self.encoded, length)
    self.encoded >>= length
    return bits

  def decode_bool(self) -> bool:
    """Decodes a Boolean value."""
    return bool(self._shift(1))

  def decode_ally(self) -> Ally:
    """Decodes a compound Ally."""
    return Ally(self._shift(_ALLY_LEN))
  
  def decode_ally_loyalty(self) -> Ally:
    """Decodes a compound Ally masked by LOYALTY_MASK."""
    return Ally(self._shift(_ALLY_LOYALTY_LEN))

  def decode_ally_optional(self) -> Ally:
    """Decodes a compound Ally masked by OPTIONAL."""
    return Ally(self._shift(_ALLY_OPTIONAL_LEN) << _ALLY_OPTIONAL_SHIFT)

  def decode_ally_index(self) -> Ally:
    """Decodes an index as an Ally."""
    index = self._shift(_ALLY_INDEX_LEN)
    return Ally(1 << (index - 1)) if index > 0 else NOBODY

  def decode_squad(self) -> Ally:
    """Decodes two indices as a compound Ally."""
    squad = self.decode_ally_index()
    return squad | self.decode_ally_index()

  def decode_choices(self) -> tuple[bool, list[Ally]]:
    """Decodes two indices with a preceding bit indicating whether the last
    non-zero index should be treated as an opposite choice.
    
    The semantics of this value and the phrase "opposite choice" are
    context-dependent.
    """
    invert_last = self.decode_bool()
    choices = []
    for i in range(2):
      choice = self.decode_ally_index()
      if choice:
        choices.append(choice)
    return invert_last, choices


def decode_outcome(encoded: int) -> dict[str, Any]:
  """Decodes outcome data from an int."""
  outcome = {}
  decoder = Decoder(encoded)
  outcome['spared'] = (spared := decoder.decode_ally())
  outcome['dead'] = decoder.decode_ally_optional() | REQUIRED & ~spared
  outcome['loyalty'] = decoder.decode_ally_loyalty() | Ally.Morinth & spared
  outcome['crew'] = decoder.decode_bool()
  return outcome