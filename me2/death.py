import statistics
from typing import Callable, TypeVar

from .ally import Ally
from . import bits

# Helper functions to avoid ".value" everywhere
def _value_list(*allies: Ally) -> list[int]:
  """Constructs a list of integer values from the given Ally enumeration
  objects."""
  return [ally.value for ally in allies]

_T = TypeVar('_T')
def _value_dict(mapping: dict[Ally, _T]) -> dict[int, _T]:
  """Constructs a dictionary with integer keys equivalent to the given mapping
  with Ally enumeration objects as keys."""
  return {ally.value: value for ally, value in mapping.items()}

# The following lists indicate the order in which allies are selected for
# death when certain conditions are met.
# Reference: https://external-preview.redd.it/7SeMlQbU-xFC9TjKurncqx1y8NH3RJiolYRqFAoXfWg.jpg?auto=webp&s=a57ad480a357234ec7fa5f865b00b60b95670df0

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

# Chose a disloyal or non-specialist biotic for The Long Walk.
DP_THE_LONG_WALK = _value_list(
  Ally.Thane, Ally.Jack, Ally.Garrus, Ally.Legion, Ally.Grunt, Ally.Samara,
  Ally.Jacob, Ally.Mordin, Ally.Tali, Ally.Kasumi, Ally.Zaeed, Ally.Morinth
)

# The average defense score is too low for the defending allies during the final
# battle. Unlike the other death priority lists, non-loyal allies are
# prioritized above loyal allies (see get_defense_victims()).
_DP_DEFENSE = _value_list(
  Ally.Mordin, Ally.Tali, Ally.Kasumi, Ally.Jack, Ally.Miranda, Ally.Jacob,
  Ally.Garrus, Ally.Samara, Ally.Morinth, Ally.Legion, Ally.Thane, Ally.Zaeed,
  Ally.Grunt
)

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
  lambda x: 1 if x < 2 else 0,
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

def _get_defense_toll(team: int, loyal: int) -> int:
  """Computes the death toll for the defense team."""
  if not (team_size := bits.popcount(team)):
    raise ValueError('Zero defending allies')
  # Compute the average defense score. Disloyal allies' scores are reduced.
  score = statistics.fmean(
    _DEFENSE_SCORE[a] - bool(a & ~loyal) for a in bits.bits(team))
  if team_size < len(_DEFENSE_TOLL_FORMULAE):
    return _DEFENSE_TOLL_FORMULAE[team_size](score)
  return _DEFENSE_TOLL_FORMULAE[-1](score)

def get_defense_victims(defense_team: int, loyal: int) -> int:
  """Selects the defending teammates who should die."""
  victims = 0
  toll = _get_defense_toll(defense_team, loyal)
  if toll == 0:
    return victims
  # Disloyal allies are prioritized over loyal ones.
  for ally in _DP_DEFENSE:
    if ally & defense_team & ~loyal:
      victims |= ally
      toll -= 1
      if toll == 0:
        break
  else:
    # NOTE: get_victim() is intentionally not reused here to avoid redundant
    # iterations of _DP_DEFENSE.
    for ally in _DP_DEFENSE:
      if ally & defense_team:
        victims |= ally
        toll -= 1
        if toll == 0:
          break
  return victims