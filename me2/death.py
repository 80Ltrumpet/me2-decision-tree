from statistics import fmean as _fmean
from typing import Callable

from .bits import popcount as _popcount
from .defs import Ally

#
# Death Priorities
#

# The following lists indicate the order in which allies are selected for
# death when certain conditions are met.

# The "Silaris Armor" upgrade was not purchased.
DP_NO_ARMOR_UPGRADE = [Ally.Jack]

# The "Cyclonic Shields" upgrade was not purchased.
DP_NO_SHIELD_UPGRADE = [
  Ally.Kasumi, Ally.Legion, Ally.Tali, Ally.Thane,
  Ally.Garrus, Ally.Zaeed, Ally.Grunt, Ally.Samara,
  Ally.Morinth
]

# The "Thanix Cannon" upgrade was not purchased.
DP_NO_WEAPON_UPGRADE = [
  Ally.Thane, Ally.Garrus, Ally.Zaeed, Ally.Grunt,
  Ally.Jack, Ally.Samara, Ally.Morinth
]

# Chose a disloyal or non-specialist biotic for The Long Walk.
DP_THE_LONG_WALK = [
  Ally.Thane, Ally.Jack, Ally.Garrus, Ally.Legion,
  Ally.Grunt, Ally.Samara, Ally.Jacob, Ally.Mordin,
  Ally.Tali, Ally.Kasumi, Ally.Zaeed, Ally.Morinth
]

# The average defense score is too low for the defending allies during the final
# battle. Unlike the other death priority lists, non-loyal allies are
# prioritized above loyal allies (see get_defense_victim()).
_DP_DEFENSE = [
  Ally.Mordin, Ally.Tali, Ally.Kasumi, Ally.Jack,
  Ally.Miranda, Ally.Jacob, Ally.Garrus, Ally.Samara,
  Ally.Morinth, Ally.Legion, Ally.Thane, Ally.Zaeed,
  Ally.Grunt
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

def get_defense_toll(defense_team: int, loyal: int) -> int:
  """Computes the death toll for the defense team."""
  if not (team_size := len(defense_team)):
    raise ValueError('Zero defending allies')
  # Compute the average defense score. Disloyal allies' scores are reduced.
  score = _fmean(_DEFENSE_SCORE[a] - bool(a & ~loyal) for a in defense_team)
  if team_size < len(_DEFENSE_TOLL_FORMULA):
    return _DEFENSE_TOLL_FORMULA[team_size](score)
  return _DEFENSE_TOLL_FORMULA[-1](score)