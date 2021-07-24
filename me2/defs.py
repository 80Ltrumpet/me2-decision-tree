from __future__ import annotations
from enum import auto as _auto, Flag as _Flag
from statistics import fmean as _fmean
from typing import Callable, Generator

from .bits import bits as _bits, ffs as _ffs, mask as _mask, mtz as _mtz
from .bits import popcount as _popcount

class Ally(_Flag):
  """Enumeration of all allies in Mass Effect 2."""

  # Required
  Garrus = _auto()
  Jack = _auto()
  Jacob = _auto()
  Miranda = _auto()
  Mordin = _auto()

  # Optional
  Grunt = _auto()
  Kasumi = _auto()
  Legion = _auto()
  Samara = _auto()
  Tali = _auto()
  Thane = _auto()
  Zaeed = _auto()
  # Place Morinth at the end for optimization.
  Morinth = _auto()

  def lt(self) -> Ally:
    """Returns an Ally representing all allies "less than" this Ally.
    
    This is particularly useful for reducing restart iterations, even for
    combinations, since they are guaranteed to be in sorted order.
    """
    return Ally(_mtz(self.value))

  def index(self) -> int:
    """Returns the index (ordinal value) of this Ally's LSB.
    
    Indices start from 1. An index of zero means the Ally is empty.
    """
    return _ffs(self.value) + 1

  def indices(self) -> Generator[int, None, None]:
    """Generates Ally enumeration member indices from this Ally.
    
    Indices start from 1.
    """
    return (i for i, _ in enumerate(self, 1))

  def __len__(self) -> int:
    """Counts the number of allies represented by this Ally."""
    return _popcount(self.value)

  def __iter__(self) -> Generator[Ally, None, None]:
    """Generates Ally enumeration members from this Ally."""
    return (Ally(bit) for bit in _bits(self.value))

  def __str__(self) -> str:
    """Converts this Ally into a human-readable string."""
    if self.name:
      return self.name
    if self.value == 0:
      return 'nobody'
    if self.value == _mask(len(Ally)):
      return 'everyone'
    names = sorted(ally.name for ally in self)
    if len(names) == 2:
      return ' and '.join(names)
    return f'{", ".join(names[:-1])}, and {names[-1]}'


#
# Groups and Aliases
#
# Keeping these outside of the definition of Ally ensures len(Ally) is
# equivalent to the bit length of Ally.value.
#

NOBODY = Ally(0)
EVERYONE = Ally(_mask(len(Ally)))

# These allies are required to complete the game.
REQUIRED = Ally.Garrus | Ally.Jack | Ally.Jacob | Ally.Miranda | Ally.Mordin

# To finish the game, at least three other allies must be recruited.
OPTIONAL = EVERYONE & ~REQUIRED

# Morinth is a special case because she can only be recruited by replacing
# Samara, who is technically optional.
RECRUITABLE = OPTIONAL & ~Ally.Morinth

# Similarly, when recruited, Morinth is always loyal, so her loyalty bit is
# technically redundant.
LOYALTY_MASK = ~Ally.Morinth

# If any of these are loyal and selected as the leader of the first fireteam,
# the death of the selected tech specialist may be avoided (see IDEAL_TECHS).
# If any of these are loyal and selected as the leader of the second fireteam,
# their death will be avoided (see IMMORTAL_LEADERS).
# If there are only three allies left at the end of The Long Walk, the
# second fireteam leader will always survive.
IDEAL_LEADERS = Ally.Garrus | Ally.Jacob | Ally.Miranda

# If any of these are loyal and selected as the tech specialist, their death
# will be avoided as long as a loyal leader is selected from IDEAL_LEADERS
# during The Infiltration.
IDEAL_TECHS = Ally.Kasumi | Ally.Legion | Ally.Tali

# If any of these are loyal and selected as the biotic specialist, the death
# of an ally will be avoided.
IDEAL_BIOTICS = Ally.Jack | Ally.Samara | Ally.Morinth

# Only overtly biotic allies can be selected as the biotic specialist.
BIOTICS = IDEAL_BIOTICS | Ally.Jacob | Ally.Miranda | Ally.Thane

# Miranda cannot be selected to escort the crew.
ESCORTS = EVERYONE & ~Ally.Miranda

# If Miranda is selected to lead the second fireteam, she will not die even if
# she is not loyal.
IMMORTAL_LEADERS = Ally.Miranda