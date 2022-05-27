#
# Copyright (c) 2022 Andrew Lehmer
#
# Distributed under the MIT License.
#

import statistics
from collections.abc import Callable
from functools import partial, reduce
from itertools import chain
from operator import or_ as op_or, and_ as op_and
from typing import TypeVar

from .ally import Ally
from . import bits

# Helper functions to avoid ".value" everywhere
def _value_list(*allies: Ally) -> list[int]:
  """Constructs a list of integer values from the given Ally enumeration
  objects."""
  return [ally.value for ally in allies]

_T = TypeVar("_T")
def _value_dict(mapping: dict[Ally, _T]) -> dict[int, _T]:
  """Constructs a dictionary with integer keys equivalent to the given
  mapping's Ally keys."""
  return {ally.value: value for ally, value in mapping.items()}

# The following lists indicate the order in which allies are selected for
# death (i.e., the "death priority") when certain conditions are met.

# The "Silaris Armor" upgrade was not purchased.
DP_NO_ARMOR_UPGRADE = _value_list(Ally.Jack)

# The "Cyclonic Shields" upgrade was not purchased.
DP_NO_SHIELD_UPGRADE = _value_list(
  Ally.Kasumi, Ally.Legion, Ally.Tali, Ally.Thane, Ally.Garrus, Ally.Zaeed,
  Ally.Grunt, Ally.Samara, Ally.Morinth
)

# The "Thanix Cannon" upgrade was not purchased.
DP_NO_WEAPON_UPGRADE = _value_list(
  Ally.Thane, Ally.Garrus, Ally.Zaeed, Ally.Grunt, Ally.Jack, Ally.Samara,
  Ally.Morinth
)

# A disloyal or non-specialist biotic was chosen for The Long Walk.
DP_THE_LONG_WALK = _value_list(
  Ally.Thane, Ally.Jack, Ally.Garrus, Ally.Legion, Ally.Grunt, Ally.Samara,
  Ally.Jacob, Ally.Mordin, Ally.Tali, Ally.Kasumi, Ally.Zaeed, Ally.Morinth
)

# The average defense score was too low for the defending allies during the
# final battle. Unlike the other death priority lists, non-loyal allies are
# prioritized above loyal allies (see get_defense_victims()).
_DP_DEFENSE = _value_list(
  Ally.Mordin, Ally.Tali, Ally.Kasumi, Ally.Jack, Ally.Miranda, Ally.Jacob,
  Ally.Garrus, Ally.Samara, Ally.Morinth, Ally.Legion, Ally.Thane, Ally.Zaeed,
  Ally.Grunt
)

class UnexpectedlyVictimlessError(Exception):
  """Custom error type for a call to get_victim() resulting in zero victims."""
  pass

def get_victim(team: int, priority: list[int]) -> int:
  """Selects the teammate who should die based on the given priority."""
  if (victim := next(filter(partial(op_and, team), priority), 0)):
    return victim
  # It should be impossible to encounter a situation where none of the teammates
  # are in the priority list.
  raise UnexpectedlyVictimlessError(
    f"No victim ({hex(team)} & {hex(reduce(op_or, priority, 0))} == 0)")


# Loyal allies who are left behind to defend during the final battle are
# assigned defense scores according to their "innate defensiveness". If an ally
# is disloyal, their score is decreased by 1 (see _get_defense_toll() below).
_DEFENSE_SCORE = _value_dict({
  Ally.Garrus: 4,
  Ally.Grunt: 4,
  Ally.Jack: 1,
  Ally.Jacob: 2,
  Ally.Kasumi: 1,
  Ally.Legion: 2,
  Ally.Miranda: 2,
  Ally.Mordin: 1,
  Ally.Samara: 2,
  Ally.Tali: 1,
  Ally.Thane: 2,
  Ally.Zaeed: 4,
  Ally.Morinth: 2
})

# Lookup table for the number of defending allies who will die according to the
# mean of their defense scores. If there are more than five allies, apply the
# last formula in this list.
_DEFENSE_TOLL_FORMULAE: list[Callable[[float], int]] = [
  int,
  (lambda x: 1 if x < 2 else 0),
  (lambda x: 2 if x == 0
        else 1 if x < 2
        else 0),
  (lambda x: 3 if x == 0
        else 2 if x < 1
        else 1 if x < 2
        else 0),
  (lambda x: 4 if x == 0
        else 3 if x < 0.5
        else 2 if x <= 1
        else 1 if x < 2
        else 0),
  (lambda x: 3 if x < 0.5
        else 2 if x < 1.5
        else 1 if x < 2
        else 0)
]
_DTF_LAST_INDEX = len(_DEFENSE_TOLL_FORMULAE) - 1

def _get_defense_toll(team: int, loyal: int) -> int:
  """Computes the death toll for the defense team."""
  if not (team_size := bits.popcount(team)):
    raise ValueError("Zero defending allies")
  # Compute the average defense score. Disloyal allies' scores are reduced.
  score_for = lambda ally: _DEFENSE_SCORE[ally] - bool(ally & ~loyal)
  score = statistics.fmean(score_for(ally) for ally in bits.bits(team))
  formula_index = min(team_size, _DTF_LAST_INDEX)
  return _DEFENSE_TOLL_FORMULAE[formula_index](score)

def get_defense_victims(team: int, loyal: int) -> int:
  """Selects the defending teammates who should die."""
  toll = _get_defense_toll(team, loyal)
  # Disloyal teammates are chosen as victims before loyal ones.
  disloyal_filter = filter(partial(op_and, team & ~loyal), _DP_DEFENSE)
  loyal_filter = filter(partial(op_and, team & loyal), _DP_DEFENSE)
  priority = chain(disloyal_filter, loyal_filter)
  return reduce(op_or, (ally for _, ally in zip(range(toll), priority)), 0)