import statistics
from typing import Callable

from .ally import Ally
from . import bits

# The following lists indicate the order in which allies are selected for
# death when certain conditions are met.
# Reference: https://external-preview.redd.it/7SeMlQbU-xFC9TjKurncqx1y8NH3RJiolYRqFAoXfWg.jpg?auto=webp&s=a57ad480a357234ec7fa5f865b00b60b95670df0

# The "Silaris Armor" upgrade was not purchased.
DP_NO_ARMOR_UPGRADE = [Ally.Jack.value]

# The "Cyclonic Shields" upgrade was not purchased.
DP_NO_SHIELD_UPGRADE = [
  Ally.Kasumi.value, Ally.Legion.value, Ally.Tali.value, Ally.Thane.value,
  Ally.Garrus.value, Ally.Zaeed.value, Ally.Grunt.value, Ally.Samara.value,
  Ally.Morinth.value
]

# The "Thanix Cannon" upgrade was not purchased.
DP_NO_WEAPON_UPGRADE = [
  Ally.Thane.value, Ally.Garrus.value, Ally.Zaeed.value, Ally.Grunt.value,
  Ally.Jack.value, Ally.Samara.value, Ally.Morinth.value
]

# Chose a disloyal or non-specialist biotic for The Long Walk.
DP_THE_LONG_WALK = [
  Ally.Thane.value, Ally.Jack.value, Ally.Garrus.value, Ally.Legion.value,
  Ally.Grunt.value, Ally.Samara.value, Ally.Jacob.value, Ally.Mordin.value,
  Ally.Tali.value, Ally.Kasumi.value, Ally.Zaeed.value, Ally.Morinth.value
]

# The average defense score is too low for the defending allies during the final
# battle. Unlike the other death priority lists, non-loyal allies are
# prioritized above loyal allies (see get_defense_victims()).
_DP_DEFENSE = [
  Ally.Mordin.value, Ally.Tali.value, Ally.Kasumi.value, Ally.Jack.value,
  Ally.Miranda.value, Ally.Jacob.value, Ally.Garrus.value, Ally.Samara.value,
  Ally.Morinth.value, Ally.Legion.value, Ally.Thane.value, Ally.Zaeed.value,
  Ally.Grunt.value
]

def get_victim(team: int, priority: list[int]) -> int:
  """Selects the teammate who should die based on the given priority."""
  for ally in priority:
    if ally & team:
      return ally
  # It should be impossible to encounter a situation where none of the teammates
  # are in the priority list.
  raise RuntimeError("No victim")


# Loyal allies who are left behind to defend during the final battle are
# assigned defense scores according to their "innate defensiveness". If an ally
# is disloyal, their score is decreased by 1 (see get_defense_toll()).
_DEFENSE_SCORE = {
  Ally.Garrus.value: 4,
  Ally.Grunt.value: 4,
  Ally.Jack.value: 1,
  Ally.Jacob.value: 2,
  Ally.Kasumi.value: 1,
  Ally.Legion.value: 2,
  Ally.Miranda.value: 2,
  Ally.Mordin.value: 1,
  Ally.Samara.value: 2,
  Ally.Tali.value: 1,
  Ally.Thane.value: 2,
  Ally.Zaeed.value: 4,
  Ally.Morinth.value: 2
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

def _get_defense_toll(team: int, loyal: int) -> int:
  """Computes the death toll for the defense team."""
  if not (team_size := bits.popcount(team)):
    raise ValueError('Zero defending allies')
  # Compute the average defense score. Disloyal allies' scores are reduced.
  score = statistics.fmean(
    _DEFENSE_SCORE[a] - bool(a & ~loyal) for a in bits.bits(team))
  if team_size < len(_DEFENSE_TOLL_FORMULA):
    return _DEFENSE_TOLL_FORMULA[team_size](score)
  return _DEFENSE_TOLL_FORMULA[-1](score)

def get_defense_victims(defense_team: int, loyal: int) -> int:
  """Selects the defending teammates who should die."""
  victims = 0
  toll = _get_defense_toll(defense_team, loyal)
  if toll == 0:
    return victims
  for ally in _DP_DEFENSE:
    if ally & defense_team & ~loyal:
      victims |= ally
      toll -= 1
      if toll == 0:
        break
  else:
    for ally in _DP_DEFENSE:
      if ally & defense_team:
        victims |= ally
        toll -= 1
        if toll == 0:
          break
  return victims