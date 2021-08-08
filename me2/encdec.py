from typing import Any

from . import ally, bits
from .ally import Ally

_ALLY_LEN = len(Ally)
_ALLY_LOYALTY_LEN = len(ally.LOYALTY_MASK)
_ALLY_OPTIONAL_LEN = len(ally.OPTIONAL)
_ALLY_OPTIONAL_SHIFT = bits.ffs(ally.OPTIONAL.value)
_ALLY_INDEX_LEN = _ALLY_LEN.bit_length()
_ALLY_INDEX_MASK = bits.mask(_ALLY_INDEX_LEN)
_IDEAL_LEADERS_LEN = len(ally.IDEAL_LEADERS)

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

  def encode_ally(self, value: int) -> None:
    """Encodes an integer as an Ally's value.
    
    For Ally enumeration members, see encode_ally_index().
    """
    self._append(value & ally.EVERYONE.value, _ALLY_LEN)

  def encode_ally_loyalty(self, loyalty: int) -> None:
    """Encodes an integer masked by LOYALTY_MASK."""
    self._append(loyalty & ally.LOYALTY_MASK.value, _ALLY_LOYALTY_LEN)

  def encode_ally_optional(self, value: int) -> None:
    """Encodes an integer masked by OPTIONAL."""
    self._append((value & ally.OPTIONAL.value) >> _ALLY_OPTIONAL_SHIFT,
                 _ALLY_OPTIONAL_LEN)

  def encode_ally_index(self, index: int) -> None:
    """Encodes a four-bit integer representing the 1-based index of an Ally.

    The caller must provide a valid index. This requires fewer bits than
    encode_ally().
    """
    self._append(index & _ALLY_INDEX_MASK, _ALLY_INDEX_LEN)
  
  def encode_ideal_leaders(self, leaders: int) -> None:
    """Encodes available, loyal, ideal leaders as a three-bit quantity."""
    self._append(leaders & ally.IDEAL_LEADERS.value, _IDEAL_LEADERS_LEN)

  def encode_squad(self, squad: int) -> None:
    """Encodes two Ally indices based on the given squad.
    
    If squad does not contain exactly two set bits, raises a ValueError.
    """
    i = 1
    for i, index in enumerate(bits.bit_indices(squad), 1):
      if i > 2:
        raise ValueError(f'Too many squadmates: {Ally(squad)}')
      self.encode_ally_index(index + 1)
    if i != 2:
      raise ValueError(f'Not a full squad: {Ally(squad)}')

  def encode_choices(self, choices: list[int]) -> None:
    """Encodes two Ally indices with a preceding bit indicating whether the
    last non-zero index should be treated as an opposite choice.
    
    The semantics of this value and the phrase "opposite choice" are
    context-dependent.
    """
    first_choice = choices[0] if choices and choices[0] else 0
    second_choice = choices[1] if first_choice and len(choices) > 1 else 0
    self.encode_bool(len(choices) < 3)
    self.encode_ally_index(bits.ffs(first_choice) + 1)
    self.encode_ally_index(bits.ffs(second_choice) + 1)


def encode_outcome(**outcome) -> int:
  """Encodes outcome data as an int."""
  # The loyalty of dead allies does not affect the outcome.
  loyalty = outcome['spared'] & outcome['loyalty']
  encoder = Encoder()
  encoder.encode_ally(outcome['spared'])
  # TODO: Optional allies that are not recruited are as good as dead, so they
  #       don't actually affect the outcome.
  encoder.encode_ally_optional(outcome['dead'])
  encoder.encode_ally_loyalty(loyalty)
  encoder.encode_bool(outcome['crew'])
  return encoder.result


class Decoder:
  """Decodes a bit-packed value with a potentially variable sequence."""
  def __init__(self, encoded: int) -> None:
    self.encoded = encoded

  def _shift(self, length: int) -> int:
    encoded = self.encoded & bits.mask(length)
    self.encoded >>= length
    return encoded

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
    return Ally(1 << (index - 1)) if index > 0 else ally.NOBODY

  def decode_ideal_leaders(self) -> Ally:
    """Decodes a compound Ally masked by IDEAL_LEADERS."""
    return Ally(self._shift(_IDEAL_LEADERS_LEN))

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
  outcome['dead'] = decoder.decode_ally_optional() | ally.REQUIRED & ~spared
  outcome['loyalty'] = decoder.decode_ally_loyalty() | Ally.Morinth & spared
  outcome['crew'] = decoder.decode_bool()
  return outcome