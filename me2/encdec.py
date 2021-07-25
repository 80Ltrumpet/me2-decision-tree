from typing import Any

from .ally import Ally as _Ally, EVERYONE as _EVERYONE
from .ally import LOYALTY_MASK as _LOYALTY_MASK, NOBODY as _NOBODY
from .ally import OPTIONAL as _OPTIONAL, REQUIRED as _REQUIRED
from .bits import bit_indices as _bit_indices, ffs as _ffs, mask as _mask
from .bits import popcount as _popcount

_ALLY_LEN = len(_Ally)
_ALLY_LOYALTY_LEN = _popcount(_LOYALTY_MASK.value)
_ALLY_OPTIONAL_LEN = _popcount(_OPTIONAL.value)
_ALLY_OPTIONAL_SHIFT = _ffs(_OPTIONAL.value)
_ALLY_INDEX_LEN = _ALLY_LEN.bit_length()
_ALLY_INDEX_MASK = _mask(_ALLY_INDEX_LEN)

class Encoder:
  """Facilitates bit-packing various types in a variable sequence."""
  def __init__(self) -> None:
    """Initializes the result to zero."""
    self.result = 0
    self.length = 0

  def _append(self, bits: int, length: int) -> None:
    self.result |= bits << self.length
    self.length += length

  def encode_bool(self, value: bool) -> None:
    """Encodes a bool as a single bit."""
    self._append(value, 1)

  def encode_ally(self, ally: int) -> None:
    """Encodes an integer as an Ally's value.
    
    For Ally enumeration members, see encode_ally_index().
    """
    self._append(ally & _EVERYONE.value, _ALLY_LEN)

  def encode_ally_loyalty(self, loyalty: int) -> None:
    """Encodes an integer masked by LOYALTY_MASK."""
    self._append(loyalty & _LOYALTY_MASK.value, _ALLY_LOYALTY_LEN)

  def encode_ally_optional(self, ally: int) -> None:
    """Encodes an integer masked by OPTIONAL."""
    self._append((ally & _OPTIONAL.value) >> _ALLY_OPTIONAL_SHIFT,
                  _ALLY_OPTIONAL_LEN)

  def encode_ally_index(self, index: int) -> None:
    """Encodes a four-bit integer representing the 1-based index of an Ally.

    The caller must provide a valid index. This requires fewer bits than
    encode_ally().
    """
    self._append(index & _ALLY_INDEX_MASK, _ALLY_INDEX_LEN)

  def encode_squad(self, squad: int) -> None:
    """Encodes two Ally indices based on the given squad.
    
    If squad does not contain exactly two set bits, raises a ValueError.
    """
    i = 1
    for i, index in enumerate(_bit_indices(squad), 1):
      if i > 2:
        raise ValueError(f'Too many squadmates: {_Ally(squad)}')
      self.encode_ally_index(index + 1)
    if i != 2:
      raise ValueError(f'Not a full squad: {_Ally(squad)}')

  def encode_choices(self, choices: list[int]) -> None:
    """Encodes two Ally indices with a preceding bit indicating whether the
    last non-zero index should be treated as an opposite choice.
    
    The semantics of this value and the phrase "opposite choice" are
    context-dependent.
    """
    first_choice = choices[0] if choices and choices[0] else 0
    second_choice = choices[1] if first_choice and len(choices) > 1 else 0
    self.encode_bool(len(choices) < 3)
    self.encode_ally_index(_ffs(first_choice) + 1)
    self.encode_ally_index(_ffs(second_choice) + 1)


def encode_outcome(**outcome) -> int:
  """Encodes outcome data as an int."""
  # The loyalty of dead allies does not affect the outcome.
  loyalty = outcome['spared'] & outcome['loyalty']
  encoder = Encoder()
  encoder.encode_ally(outcome['spared'])
  encoder.encode_ally_optional(outcome['dead'])
  encoder.encode_ally_loyalty(loyalty)
  encoder.encode_bool(outcome['crew'])
  return encoder.result


class Decoder:
  """Decodes a bit-packed value with a potentially variable sequence."""
  def __init__(self, encoded: int) -> None:
    self.encoded = encoded

  def _shift(self, length: int) -> int:
    bits = self.encoded & _mask(length)
    self.encoded >>= length
    return bits

  def decode_bool(self) -> bool:
    """Decodes a Boolean value."""
    return bool(self._shift(1))

  def decode_ally(self) -> _Ally:
    """Decodes a compound Ally."""
    return _Ally(self._shift(_ALLY_LEN))
  
  def decode_ally_loyalty(self) -> _Ally:
    """Decodes a compound Ally masked by LOYALTY_MASK."""
    return _Ally(self._shift(_ALLY_LOYALTY_LEN))

  def decode_ally_optional(self) -> _Ally:
    """Decodes a compound Ally masked by OPTIONAL."""
    return _Ally(self._shift(_ALLY_OPTIONAL_LEN) << _ALLY_OPTIONAL_SHIFT)

  def decode_ally_index(self) -> _Ally:
    """Decodes an index as an Ally."""
    index = self._shift(_ALLY_INDEX_LEN)
    return _Ally(1 << (index - 1)) if index > 0 else _NOBODY

  def decode_squad(self) -> _Ally:
    """Decodes two indices as a compound Ally."""
    squad = self.decode_ally_index()
    return squad | self.decode_ally_index()

  def decode_choices(self) -> tuple[bool, list[_Ally]]:
    """Decodes two indices with a preceding bit indicating whether the last
    non-zero index should be treated as an opposite choice.
    
    The semantics of this value and the phrase "opposite choice" are
    context-dependent.
    """
    invert_last = self.decode_bool()
    choices = []
    for _ in range(2):
      choice = self.decode_ally_index()
      if choice:
        choices.append(choice)
    return invert_last, choices


def decode_outcome(encoded: int) -> dict[str, Any]:
  """Decodes outcome data from an int."""
  outcome: dict[str, Any] = {}
  decoder = Decoder(encoded)
  outcome['spared'] = (spared := decoder.decode_ally())
  outcome['dead'] = decoder.decode_ally_optional() | _REQUIRED & ~spared
  outcome['loyalty'] = decoder.decode_ally_loyalty() | _Ally.Morinth & spared
  outcome['crew'] = decoder.decode_bool()
  return outcome