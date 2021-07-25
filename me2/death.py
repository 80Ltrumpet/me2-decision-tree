from statistics import fmean as _fmean
from typing import Callable

from .bits import bits as _bits, popcount as _popcount
from .ally import Ally as _Ally

#
# Death Priorities
#

# The following lists indicate the order in which allies are selected for
# death when certain conditions are met.

# The "Silaris Armor" upgrade was not purchased.
DP_NO_ARMOR_UPGRADE = [_Ally.Jack.value]

# The "Cyclonic Shields" upgrade was not purchased.
DP_NO_SHIELD_UPGRADE = [
  _Ally.Kasumi.value, _Ally.Legion.value, _Ally.Tali.value, _Ally.Thane.value,
  _Ally.Garrus.value, _Ally.Zaeed.value, _Ally.Grunt.value, _Ally.Samara.value,
  _Ally.Morinth.value
]

# The "Thanix Cannon" upgrade was not purchased.
DP_NO_WEAPON_UPGRADE = [
  _Ally.Thane.value, _Ally.Garrus.value, _Ally.Zaeed.value, _Ally.Grunt.value,
  _Ally.Jack.value, _Ally.Samara.value, _Ally.Morinth.value
]

# Chose a disloyal or non-specialist biotic for The Long Walk.
DP_THE_LONG_WALK = [
  _Ally.Thane.value, _Ally.Jack.value, _Ally.Garrus.value, _Ally.Legion.value,
  _Ally.Grunt.value, _Ally.Samara.value, _Ally.Jacob.value, _Ally.Mordin.value,
  _Ally.Tali.value, _Ally.Kasumi.value, _Ally.Zaeed.value, _Ally.Morinth.value
]

# The average defense score is too low for the defending allies during the final
# battle. Unlike the other death priority lists, non-loyal allies are
# prioritized above loyal allies (see get_defense_victim()).
_DP_DEFENSE = [
  _Ally.Mordin.value, _Ally.Tali.value, _Ally.Kasumi.value, _Ally.Jack.value,
  _Ally.Miranda.value, _Ally.Jacob.value, _Ally.Garrus.value, _Ally.Samara.value,
  _Ally.Morinth.value, _Ally.Legion.value, _Ally.Thane.value, _Ally.Zaeed.value,
  _Ally.Grunt.value
]

def get_victim(team: int, priority: list[int]) -> int:
  """Selects the teammate who should die based on the given priority."""
  for ally in priority:
    if ally & team:
      return ally
  # It should be impossible to encounter a situation where none of the teammates
  # are in the priority list.
  raise RuntimeError("No victim")

def get_defense_victim(defense_team: int, loyal: int) -> int:
  """Selects the defending teammate who should die."""
  # If everyone is loyal, this is the same as get_victim().
  if defense_team == defense_team & loyal:
    return get_victim(defense_team, _DP_DEFENSE)
  for ally in _DP_DEFENSE:
    if ally & defense_team & ~loyal:
      return ally
  return get_victim(defense_team, _DP_DEFENSE)


#
# Defense Scoring
#

# Loyal allies who are left behind to defend during the final battle are
# assigned defense scores according to their "innate defensiveness". If an ally
# is disloyal, their score is decreased by 1 (see get_defense_toll()).
_DEFENSE_SCORE = {
  _Ally.Garrus.value: 4,
  _Ally.Grunt.value: 4,
  _Ally.Jack.value: 1,
  _Ally.Jacob.value: 2,
  _Ally.Kasumi.value: 1,
  _Ally.Legion.value: 2,
  _Ally.Miranda.value: 2,
  _Ally.Mordin.value: 1,
  _Ally.Samara.value: 2,
  _Ally.Tali.value: 1,
  _Ally.Thane.value: 2,
  _Ally.Zaeed.value: 4,
  _Ally.Morinth.value: 2
}

# Lookup table for the number of defending allies who will die according to the
# mean of their defense scores. If there are more than five allies, apply the
# last formula in this list.
_DEFENSE_TOLL_FORMULA: list[Callable[[float], int]] = [
  int,
  lambda x: 1 if x < 2 else 0,
  lambda x: 2 if x == 0 else 1 if x < 2 else 0,
  lambda x: 3 if x == 0 else 2 if x < 1 else 1 if x < 2 else 0,
  lambda x: 4 if x == 0 else 3 if x < 0.5 else 2 if x <= 1 else 1 if x < 2 else 0,
  lambda x: 3 if x < 0.5 else 2 if x < 1.5 else 1 if x < 2 else 0
]

def get_defense_toll(team: int, loyal: int) -> int:
  """Computes the death toll for the defense team."""
  if not (team_size := _popcount(team)):
    raise ValueError('Zero defending allies')
  # Compute the average defense score. Disloyal allies' scores are reduced.
  score = _fmean(_DEFENSE_SCORE[a] - bool(a & ~loyal) for a in _bits(team))
  if team_size < len(_DEFENSE_TOLL_FORMULA):
    return _DEFENSE_TOLL_FORMULA[team_size](score)
  return _DEFENSE_TOLL_FORMULA[-1](score)