from __future__ import annotations
import enum
from typing import Generator

from . import bits

class Ally(enum.Flag):
  """Enumeration of all allies in Mass Effect 2."""

  # Required
  # Group Garrus, Jacob, and Miranda (ideal leaders) together for optimization.
  Garrus = enum.auto()
  Jacob = enum.auto()
  Miranda = enum.auto()
  Jack = enum.auto()
  Mordin = enum.auto()

  # Optional
  Grunt = enum.auto()
  Kasumi = enum.auto()
  Legion = enum.auto()
  Samara = enum.auto()
  Tali = enum.auto()
  Thane = enum.auto()
  Zaeed = enum.auto()
  # Place Morinth at the end for optimization.
  Morinth = enum.auto()

  def conj(self, conjunction: str = 'and') -> str:
    """Converts this Ally into a human-readable string with the specified
    conjunction, if applicable."""
    if self.name:
      return self.name
    if self.value == 0:
      return 'nobody'
    if self.value == bits.mask(len(Ally)):
      return 'everyone'
    names = sorted(ally.name for ally in self)
    if len(names) == 2:
      return f' {conjunction} '.join(names)
    return f'{", ".join(names[:-1])}, {conjunction} {names[-1]}'

  def __len__(self) -> int:
    """Counts the number of allies represented by this Ally."""
    return bits.popcount(self.value)

  def __iter__(self) -> Generator[Ally, None, None]:
    """Generates Ally enumeration members from this Ally."""
    return (Ally(bit) for bit in bits.bits(self.value))

  def __str__(self) -> str:
    """Converts this Ally into a human-readable string."""
    return self.conj()


#
# Groups and Aliases
#
# Keeping these outside of the definition of Ally ensures len(Ally) is
# equivalent to the bit length of Ally.value.
#

NOBODY = Ally(0)
EVERYONE = Ally(bits.mask(len(Ally)))

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

# If any of these are loyal and selected as the leader of the second fireteam,
# the death of the selected tech specialist may be avoided (see IDEAL_TECHS).
# If any of these are loyal and selected as the leader of the diversion team,
# their death will be avoided (see IMMORTAL_LEADERS).
# If there are only three allies left at the end of The Long Walk, the
# diversion team leader will always survive.
IDEAL_LEADERS = Ally.Garrus | Ally.Jacob | Ally.Miranda

# If any of these are loyal and selected as the tech specialist, their death
# will be avoided as long as a loyal leader is selected from IDEAL_LEADERS
# during The Infiltration.
IDEAL_TECHS = Ally.Kasumi | Ally.Legion | Ally.Tali

# If any of these are loyal and selected as the biotic specialist, the death
# of an ally will be avoided.
IDEAL_BIOTICS = Ally.Jack | Ally.Samara | Ally.Morinth

# NOTE: There is no limitation on who can be selected as a leader.

# Only certain allies can be selected as the tech specialist.
TECHS = IDEAL_TECHS | Ally.Garrus | Ally.Jacob | Ally.Mordin | Ally.Thane

# Only overtly biotic allies can be selected as the biotic specialist.
BIOTICS = IDEAL_BIOTICS | Ally.Jacob | Ally.Miranda | Ally.Thane

# Miranda cannot be selected to escort the crew.
ESCORTS = EVERYONE & ~Ally.Miranda

# If Miranda is selected to lead the second fireteam, she will not die even if
# she is not loyal.
IMMORTAL_LEADERS = Ally.Miranda