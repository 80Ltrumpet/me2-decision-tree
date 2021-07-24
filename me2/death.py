from statistics import fmean as _fmean
from typing import Callable

from .bits import popcount as _popcount
from .ally import Ally as _Ally

#
# Death Priorities
#

# The following lists indicate the order in which allies are selected for
# death when certain conditions are met.

# The "Silaris Armor" upgrade was not purchased.
DP_NO_ARMOR_UPGRADE = [_Ally.Jack]

# The "Cyclonic Shields" upgrade was not purchased.
DP_NO_SHIELD_UPGRADE = [
  _Ally.Kasumi, _Ally.Legion, _Ally.Tali, _Ally.Thane,
  _Ally.Garrus, _Ally.Zaeed, _Ally.Grunt, _Ally.Samara,
  _Ally.Morinth
]

# The "Thanix Cannon" upgrade was not purchased.
DP_NO_WEAPON_UPGRADE = [
  _Ally.Thane, _Ally.Garrus, _Ally.Zaeed, _Ally.Grunt,
  _Ally.Jack, _Ally.Samara, _Ally.Morinth
]

# Chose a disloyal or non-specialist biotic for The Long Walk.
DP_THE_LONG_WALK = [
  _Ally.Thane, _Ally.Jack, _Ally.Garrus, _Ally.Legion,
  _Ally.Grunt, _Ally.Samara, _Ally.Jacob, _Ally.Mordin,
  _Ally.Tali, _Ally.Kasumi, _Ally.Zaeed, _Ally.Morinth
]

# The average defense score is too low for the defending allies during the final
# battle. Unlike the other death priority lists, non-loyal allies are
# prioritized above loyal allies (see get_defense_victim()).
_DP_DEFENSE = [
  _Ally.Mordin, _Ally.Tali, _Ally.Kasumi, _Ally.Jack,
  _Ally.Miranda, _Ally.Jacob, _Ally.Garrus, _Ally.Samara,
  _Ally.Morinth, _Ally.Legion, _Ally.Thane, _Ally.Zaeed,
  _Ally.Grunt
]

def get_victim(team: _Ally, priority: list[_Ally]) -> _Ally:
  """Selects the teammate who should die based on the given priority."""
  for ally in priority:
    if ally & team:
      return ally
  # It should be impossible to encounter a situation where none of the teammates
  # are in the priority list.
  raise RuntimeError("No victim")

def get_defense_victim(defense_team: _Ally, loyal: _Ally) -> _Ally:
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
  _Ally.Garrus: 4,
  _Ally.Grunt: 4,
  _Ally.Jack: 1,
  _Ally.Jacob: 2,
  _Ally.Kasumi: 1,
  _Ally.Legion: 2,
  _Ally.Miranda: 2,
  _Ally.Mordin: 1,
  _Ally.Samara: 2,
  _Ally.Tali: 1,
  _Ally.Thane: 2,
  _Ally.Zaeed: 4,
  _Ally.Morinth: 2
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

def get_defense_toll(defense_team: _Ally, loyal: _Ally) -> int:
  """Computes the death toll for the defense team."""
  if not (team_size := len(defense_team)):
    raise ValueError('Zero defending allies')
  # Compute the average defense score. Disloyal allies' scores are reduced.
  score = _fmean(_DEFENSE_SCORE[a] - bool(a & ~loyal) for a in defense_team)
  if team_size < len(_DEFENSE_TOLL_FORMULA):
    return _DEFENSE_TOLL_FORMULA[team_size](score)
  return _DEFENSE_TOLL_FORMULA[-1](score)