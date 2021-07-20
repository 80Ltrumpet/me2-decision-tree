from __future__ import annotations
from copy import copy
from enum import auto, Enum, Flag
from functools import reduce
from itertools import combinations
from operator import or_
from pickle import Pickler, Unpickler
from signal import SIGINT, signal
from typing import Any, Callable, Generator, Optional, TypeVar

# Used for generic type annotations.
T = TypeVar('T')

#
# Bitwise Utilities
#

def bit_masks(x: int) -> Generator[int, None, None]:
  """Generates single-bit masks for bits that are set in x."""
  mask = 1
  while mask <= x:
    if mask & x:
      yield mask
    mask <<= 1

def bit_positions(x: int) -> Generator[int, None, None]:
  """Generates zero-indexed positions for bits that are set in x."""
  bit = 0
  while (mask := 1 << bit) <= x:
    if mask & x:
      yield bit
    bit += 1

def ffs(x: int) -> int:
  """Finds the position of the first set bit in x or -1 if no bits are set."""
  return next(bit_positions(x), -1)

def lsb(x: int) -> int:
  """Returns the value of the first set bit in x or 0 if no bits are set."""
  return next(bit_masks(x), 0)


#
# Allies
#

class Ally(Flag):
  """Enumeration of all allies in Mass Effect 2."""

  # REQUIRED
  Garrus = auto()
  Jack = auto()
  Jacob = auto()
  Miranda = auto()
  Mordin = auto()

  # OPTIONAL
  Grunt = auto()
  Kasumi = auto()
  Legion = auto()
  Samara = auto()
  Tali = auto()
  Thane = auto()
  Zaeed = auto()
  # Place Morinth at the end for optimization.
  Morinth = auto()

  def lt(self) -> Ally:
    """Returns a compound Ally representing all allies "less than" this one.
    
    This is particularly useful for reducing restart iterations, even for
    combinations, since they are guaranteed to be in sorted order.
    """
    return Ally(lsb(self.value) - 1) if self else Ally(0)

  #
  # Useful Overrides
  #

  def __len__(self) -> int:
    """Counts the number of allies represented by this potentially compound
    Ally."""
    return bin(self.value).count('1')

  def __iter__(self) -> Generator[Ally, None, None]:
    """Generates single Ally objects from this potentially compound Ally."""
    return (Ally(mask) for mask in bit_masks(self.value))

  def __str__(self) -> str:
    if self.name:
      return self.name
    if self.value == 0:
      return 'nobody'
    if self.value == (1 << len(Ally)) - 1:
      return 'everyone'
    names = sorted(ally.name for ally in self)
    if len(names) == 2:
      return ' and '.join(names)
    return f'{", ".join(names[:-1])}, and {names[-1]}'


#
# Groups and Aliases
#
# Keeping these out of the definition of Ally prevents the interpreter from
# trying to be clever when representing dynamic groupings of allies. It
# tends to be more difficult to read and is heavily redundant.
#

NOBODY = Ally(0)
EVERYONE = Ally((1 << len(Ally)) - 1)

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

#
# Special Roles
#

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


#
# Death Priorities
#

# The following lists indicate the order in which allies are selected for
# death when certain conditions are met. If a disloyal ally on the list
# meets the conditions, they are prioritized above loyal allies according
# to the same order.

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

# The average defense score is too low for the allies holding the line
# during the final battle.
DP_HOLD_THE_LINE = [
  Ally.Mordin, Ally.Tali, Ally.Kasumi, Ally.Jack,
  Ally.Miranda, Ally.Jacob, Ally.Garrus, Ally.Samara,
  Ally.Morinth, Ally.Legion, Ally.Thane, Ally.Zaeed,
  Ally.Grunt
]


#
# Hold The Line: Scoring
#

# Loyal allies who "hold the line" in the final battle are assigned a
# "defense score" according to their "innate defensiveness". If an ally
# is disloyal, their score is decreased by 1.
DEFENSE_SCORE = {
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

# Lookup table for the number of allies who will die "holding the line"
# according to the average of their defense scores. If there are more than
# five allies, apply the last formula in this list.
HTL_TOLL_FORMULA: list[Callable[[float], int]] = [
  int,
  lambda x: 1 if x < 2 else 0,
  lambda x: 2 if x == 0 else 1 if x < 2 else 0,
  lambda x: 3 if x == 0 else 2 if x < 1 else 1 if x < 2 else 0,
  lambda x: 4 if x == 0 else 3 if x < 0.5 else 2 if x <= 1 else 1 if x < 2 else 0,
  lambda x: 3 if x < 0.5 else 2 if x < 1.5 else 1 if x < 2 else 0
]


class Team:
  """Team state tracker."""

  def __init__(self):
    """Constructs a valid initial state of the team before any decisions."""
    self.active = REQUIRED
    self.dead = NOBODY
    self.spared = NOBODY
  
  def kill(self, ally: Ally) -> Team:
    """Marks the given ally as dead."""
    self.active &= ~ally
    self.dead |= ally
    return self

  def spare(self, ally: Ally) -> Team:
    """Marks the given ally as spared."""
    self.active &= ~ally
    self.spared |= ally
    return self

  def recruit(self, ally: Ally) -> Team:
    """Adds the given ally to the team."""
    self.active |= ally
    if ally & Ally.Morinth:
      self.kill(Ally.Samara)
    return self


class DecisionTreePauseException(Exception):
  """Custom exception type for pausing execution of the decision tree."""
  pass


#
# Memo Keys
#

class MemoKey(Enum):
  N_OPT = auto()
  RECRUITS = auto()
  LOYALTY = auto()
  MORINTH = auto()
  ARMOR = auto()
  SHIELD = auto()
  CB_PICK = auto()
  WEAPON = auto()
  TECH = auto()
  LEADER1 = auto()
  BIOTIC = auto()
  LEADER2 = auto()
  CREW = auto()
  ESCORT = auto()
  WALK_UNPICK = auto()
  FINAL_SQUAD = auto()


#
# Cache Keys
#

class CacheKey(Enum):
  CARGO_BAY_PICKS = auto()
  LONG_WALK_UNPICKS = auto()


#
# Encoder
#

class Encoder:
  """Facilitates bit-packing various types in LSB-to_MSB order."""
  def __init__(self):
    self.encoded = 0
    self.index = 0

  def __int__(self):
    return self.encoded

  def shift(self, width: int) -> int:
    shift = self.index
    self.index += width
    return shift

  def encode_bool(self, value: bool) -> None:
    """Encodes a Boolean value as a single bit."""
    self.encoded |= int(bool(value)) << self.shift(1)

  def encode_ally(self, allies: Ally) -> None:
    """Encodes a compound Ally value as a full-width (13-bit) bitfield.
    
    For singular Ally values, see add_ally().
    """
    self.encoded |= allies.value << self.shift(len(Ally))

  def encode_loyal_ally(self, allies: Ally) -> None:
    """Encodes a compound Ally value masked with LOYALTY_MASK (12 bits)."""
    loyal = allies & LOYALTY_MASK
    self.encoded |= loyal.value << self.shift(len(LOYALTY_MASK))

  def encode_optional_ally(self, allies: Ally) -> None:
    """Encodes a compound Ally value masked with OPTIONAL (8 bits)."""
    optional = (allies & OPTIONAL).value >> ffs(OPTIONAL.value)
    self.encoded |= optional << self.shift(len(OPTIONAL))

  def encode_squad(self, squad: Ally, size: int = 1) -> None:
    """Encodes size 1-indexed bit positions of an Ally as 4-bit values starting
    from the first set bit."""
    for index, bit_pos in enumerate(bit_positions(squad.value)):
      if index >= size:
        return
      self.encoded |= (bit_pos + 1) << self.shift(4)
    # "Extra" squadmates are encoded as zeros.
    self.shift(4 * (size - len(squad)))

  def encode_picks(self, picks: list[Ally]) -> None:
    if not (picks and picks[0]):
      self.encode_bool(False)
      self.encode_squad(NOBODY)
    else:
      pick_count = len(picks)
      self.encode_bool(pick_count < 3)
      self.encode_squad(picks[0])
      self.encode_squad(picks[1] if pick_count > 1 else NOBODY)


#
# Decoder
#

class Decoder:
  def __init__(self, encoded: int):
    self.encoded = encoded
    self.index = 0

  def shift(self, width: int) -> int:
    shift = self.index
    self.index += width
    return shift

  def decode_bool(self) -> bool:
    return bool(self.encoded & (1 << self.shift(1)))

  def decode_ally(self) -> Ally:
    return Ally((self.encoded >> self.shift(len(Ally))) & EVERYONE.value)
  
  def decode_loyal_ally(self) -> Ally:
    loyal = self.encoded >> self.shift(len(LOYALTY_MASK))
    return Ally(loyal & LOYALTY_MASK.value)

  def decode_optional_ally(self) -> Ally:
    optional = self.encoded >> self.shift(len(OPTIONAL))
    return Ally((optional << ffs(OPTIONAL.value)) & EVERYONE.value)

  def decode_squad(self, size: int = 1) -> Ally:
    squad = NOBODY
    for _ in range(size):
      ordinal = (self.encoded >> self.shift(4)) & 0xf
      if ordinal == 0:
        break
      if ordinal > len(Ally):
        raise ValueError(f'Invalid squad encoding: {hex(ordinal)}')
      squad |= Ally(1 << (ordinal - 1))
    return squad

  def decode_picks(self) -> tuple[bool, list[Ally]]:
    invert_last = self.decode_bool()
    picks = []
    if (ally := self.decode_squad()):
      picks.append(ally)
      if (ally := self.decode_squad()):
        picks.append(ally)
    return invert_last, picks


def decode_outcome(encoded: int, *, full: bool = False) -> str:
  decoder = Decoder(encoded)
  spared = decoder.decode_ally()
  dead = decoder.decode_optional_ally() | (REQUIRED & ~spared)
  loyalty = decoder.decode_loyal_ally()
  crew = decoder.decode_bool()

  if full:
    output  = f'Survived: ({len(spared)}) {spared}\n'
    output += f'Dead:     ({len(dead)}) {dead}\n'
    if loyalty == spared & LOYALTY_MASK:
      output += 'Loyal:    everyone\n'
    else:
      output += f'Loyal:    {loyalty}\n'
    return output + f'Crew:     {"survived" if crew else "dead"}'
  
  output = f'{len(spared)} survived; {len(dead)} dead; '
  return output + f'crew {"spared" if crew else "dead"}.'

def decode_traversal(pair: tuple[int, tuple[int, int]]) -> str:
  decoder = Decoder(pair[1][1])
  loyalty = decoder.decode_loyal_ally()
  upgraded_armor = decoder.decode_bool()
  upgraded_shield = decoder.decode_bool()
  upgraded_weapon = decoder.decode_bool()
  if not upgraded_shield:
    cbs_invert, cbs_picks = decoder.decode_picks()
  tech = decoder.decode_squad()
  has_leader1 = bool(tech & loyalty & IDEAL_TECHS)
  if has_leader1:
    leader1 = decoder.decode_bool()
  biotic = decoder.decode_squad()
  leader2 = decoder.decode_squad()
  escort = decoder.decode_squad()
  has_tlw_unpicks = decoder.decode_bool()
  if has_tlw_unpicks:
    tlw_invert, tlw_unpicks = decoder.decode_picks()
  final_squad = decoder.decode_squad(2)

  output = ''
  if upgraded_armor and upgraded_shield and upgraded_weapon:
    output += 'Upgrade everything.\n'
  elif not (upgraded_armor or upgraded_shield or upgraded_weapon):
    output += 'No upgrades.\n'
  else:
    upgrade_map = {
      'Silaris Armor': upgraded_armor,
      'Cyclonic Shields': upgraded_shield,
      'Thanix Cannon': upgraded_weapon
    }
    output += f'Upgrade: {", ".join(k for k, v in upgrade_map.items() if v)}\n'

  # Recruitment is decoded from the outcome.
  decoder = Decoder(pair[0])
  everyone = decoder.decode_ally() | decoder.decode_optional_ally() | REQUIRED

  output += 'Recruit: {}\n'.format(everyone & OPTIONAL)
  if loyalty == everyone & LOYALTY_MASK:
    output += 'Do all loyalty missions.\n'
  elif not loyalty:
    output += 'Do no loyalty missions.\n'
  else:
    output += f'Loyalty Missions: {loyalty}\n'
  
  if not upgraded_shield:
    output += 'For the cargo bay squad, '
    cbs_take = reduce(or_, cbs_picks[:-1] if cbs_invert else cbs_picks, NOBODY)
    cbs_leave = cbs_picks[-1] if cbs_invert else NOBODY
    if cbs_take:
      output += f'pick {cbs_take}'
      if cbs_leave:
        output += ' and '
    if cbs_leave:
      output += f'make sure to leave {cbs_leave} behind'
    output += '.\n'
  
  output += f'Choose {tech} as the tech specialist'
  if has_leader1:
    leader_desc = 'an ideal' if leader1 else 'a non-ideal'
    output += f', and choose {leader_desc} fireteam leader.\n'
  else:
    output += '. The first fireteam leader does not matter.\n'

  output += f'Choose {biotic} as the biotic specialist '
  output += f'and {leader2} as the second fireteam leader.\n'
  if escort:
    output += f'Send {escort} to escort the crew.\n'
  else:
    output += 'Do not send anyone to escort the crew.\n'
  if has_tlw_unpicks:
    output += 'For the squad in the biotic shield, '
    tlw_take = tlw_unpicks[-1] if tlw_invert else NOBODY
    tlw_leave = \
      reduce(or_, tlw_unpicks[:-1] if tlw_invert else tlw_unpicks, NOBODY)
    if tlw_take:
      output += f'pick {tlw_take}'
      if tlw_leave:
        output += ' and '
    if tlw_leave:
      output += f'make sure to leave {tlw_leave} behind'
    output += '.\n'

  output += f'Pick {final_squad} for your final squad.\n'
  return output


# This class performs a depth-first traversal of all possible combinations of
# decisions that affect the survival of allies in Mass Effect 2's final
# mission sequence. This will generate a dictionary of all possible outcomes
# mapped to the decision sequences that produce them.
#
# Due to the highly recursive nature of the algorithm, memory usage is a
# concern. To reduce it somewhat, decision sequences and outcomes are encoded
# into a compact format for storage.
class DecisionTree:
  def __init__(self, file_path: str = 'me2.dat'):
    """Constructs a decision tree and optionally loads data from the file at the
    given file_path."""
    self.file_path = file_path
    self.loyalty = NOBODY
    self.memo: dict[str, Any] = {}
    self.outcomes: dict[int, tuple[int, int]] = {}
    self.pausing = False
    # Similar to the memo, but not persistent.
    self.cache: dict[CacheKey, Any] = {}
    # Used for marking which keys from the memo have already been read.
    self.spent_memo_keys: set[MemoKey] = set()
    self.load()
  
  def loyal(self, ally: Ally) -> bool:
    """Checks if the given ally is loyal."""
    return bool(self.loyalty & ally)

  def get_victim(self, team: Ally, priority: list[Ally]) -> Ally:
    """Selects the active teammate who should die based on the given
    priority."""
    for ally in priority:
      if ally & team:
        return ally
    raise RuntimeError("No victim")

  def get_htl_victim(self, htl_team: Ally) -> Ally:
    """Selects the "hold the line" ally who should die based on the given
    priority."""
    # If everyone is loyal, this is the same as get_victim().
    if htl_team == (htl_team & self.loyalty):
      return self.get_victim(htl_team, DP_HOLD_THE_LINE)
    for ally in DP_HOLD_THE_LINE:
      if ally & htl_team and not self.loyal(ally):
        return ally
    return self.get_victim(htl_team, DP_HOLD_THE_LINE)

  def get_htl_toll(self, htl_team: Ally) -> int:
    """Computes the death toll for the allies who "hold the line"."""
    team_size = len(htl_team)
    if team_size < 1:
      raise ValueError('Zero hold-the-line allies')
    # Compute the average defense score.
    score = 0.
    for ally in htl_team:
      score += DEFENSE_SCORE[ally]
      # Each disloyal ally subtracts 1 from the defense score total.
      if not self.loyal(ally):
        score -= 1
    score /= team_size
    if team_size < len(HTL_TOLL_FORMULA):
      return HTL_TOLL_FORMULA[team_size](score)
    return HTL_TOLL_FORMULA[-1](score)

  #
  # Outcome Encoding
  #

  def encode_outcome(self, team: Team) -> None:
    """Encodes the outcome based on the final state of the team and adds it to
    the outcome dictionary with a 2-tuple containing the number of traversals
    resulting in that outcome and an encoding of the last such traversal."""
    # The encoded outcome is 34 bits wide.
    encoder = Encoder()
    encoder.encode_ally(team.spared)
    # Only encode deaths of optional allies. Required allies that are not spared
    # are dead.
    encoder.encode_optional_ally(team.dead)
    # The loyalty of dead allies does not affect the uniqueness of the outcome.
    encoder.encode_loyal_ally(self.loyalty & team.spared)
    encoder.encode_bool(self.get_memo(MemoKey.CREW, False))
    outcome = int(encoder)

    # The bit-width of the encoded traversal is variable. (min, max) = (40, 59)
    encoder = Encoder()
    encoder.encode_loyal_ally(self.loyalty & (team.spared | team.dead))
    encoder.encode_bool(self.get_memo(MemoKey.ARMOR, True))
    encoder.encode_bool((shield := self.get_memo(MemoKey.SHIELD, True)))
    encoder.encode_bool(self.get_memo(MemoKey.WEAPON, True))
    if not shield:
      # This cache key is mandatory if the shield is not upgraded.
      encoder.encode_picks(self.cache[CacheKey.CARGO_BAY_PICKS])
    encoder.encode_squad(Ally(self.memo[MemoKey.TECH.name]))
    leader1: Optional[bool] = self.get_memo(MemoKey.LEADER1, None)
    if leader1 is not None:
      encoder.encode_bool(leader1)
    encoder.encode_squad(Ally(self.memo[MemoKey.BIOTIC.name]))
    encoder.encode_squad(Ally(self.memo[MemoKey.LEADER2.name]))
    encoder.encode_squad(self.get_memo(MemoKey.ESCORT, NOBODY))
    walk_unpick = self.get_memo(MemoKey.WALK_UNPICK, None) is not None
    encoder.encode_bool(walk_unpick)
    if walk_unpick:
      # This cache key is mandatory if the biotic is not loyal and ideal and a
      # meaningful squad selection is possible.
      encoder.encode_picks(self.cache[CacheKey.LONG_WALK_UNPICKS])
    encoder.encode_squad(self.get_memo(MemoKey.FINAL_SQUAD, NOBODY), 2)
    traversal = int(encoder)
    
    # Replace the outcome tuple.
    traversal_count = self.outcomes.get(outcome, (0, 0))[0] + 1
    self.outcomes[outcome] = (traversal_count, traversal)

  #
  # Memo
  #
  # Although the MemoKey enumeration members are used as arguments to the
  # following methods, their names are stored as the keys for optimal pickling.
  #

  def get_memo(self, key: MemoKey, default: T) -> T:
    """Gets the value of the requested memo key."""
    # Ally values are stored in the memo as integers, so this check makes their
    # retrieval less annoying and error-prone.
    if isinstance(default, Ally):
      return Ally(self.memo.get(key.name, default.value))  # type: ignore
    return self.memo.get(key.name, default)

  def read_memo(self, key: MemoKey, default: T) -> T:
    """Gets the value of the requested memo key on the first call.
    
    On subsequent calls or if the key is not in the memo, returns default.
    """
    if key in self.spent_memo_keys:
      return default
    self.spent_memo_keys.add(key)
    return self.get_memo(key, default)
  
  def write_memo(self, key: MemoKey, value: Any) -> None:
    """Sets the value for the requested memo key and checks if the user
    requested a pause."""
    self.memo[key.name] = value.value if isinstance(value, Ally) else value
    if self.pausing:
      raise DecisionTreePauseException()

  def clear_memo(self, key: MemoKey) -> None:
    """Deletes a key from the memo, whether or not it exists."""
    self.memo.pop(key.name, None)
  
  #
  # Persistence
  #

  def save(self) -> None:
    """Writes memo and outcome data to a file."""
    if not self.file_path:
      return
    with open(self.file_path, 'wb') as datafile:
      pickler = Pickler(datafile)
      pickler.dump(self.memo)
      pickler.dump(self.outcomes)

  def load(self) -> None:
    """Reads memo and outcome data from a file."""
    if not self.file_path:
      return
    try:
      with open(self.file_path, 'rb') as datafile:
        unpickler = Unpickler(datafile)
        self.memo = unpickler.load()
        self.outcomes = unpickler.load()
    except FileNotFoundError:
      print('No data file. Starting from scratch.')
  
  #
  # Runtime
  #

  def generate(self) -> None:
    """Generates decision tree outcomes."""
    # Pressing Ctrl-C gracefully pauses the operation.
    def handle_sigint(*_):
      self.pausing = True
    sigint_handler = signal(SIGINT, handle_sigint)
    try:
      self.choose_recruitment()
    except DecisionTreePauseException:
      pass
    finally:
      self.save()
    # Restore the original SIGINT handler.
    signal(SIGINT, sigint_handler)

  #
  # Decision Methods
  #

  def choose_recruitment(self) -> None:
    # At least three optional allies must be recruited to finish the game.
    n_start = self.read_memo(MemoKey.N_OPT, 3)
    if n_start == 0:
      return
    for n in range(n_start, len(RECRUITABLE) + 1):
      self.write_memo(MemoKey.N_OPT, n)
      self.choose_recruits(n)
    # This signals that all outcomes have been generated.
    self.write_memo(MemoKey.N_OPT, 0)

  def choose_recruits(self, n: int) -> None:
    # Iterate through all possible combinations of optional recruitment.
    memo_recruits = self.read_memo(MemoKey.RECRUITS, NOBODY)
    for recruits_tuple in combinations(RECRUITABLE & ~memo_recruits.lt(), n):
      recruits: Ally = reduce(or_, recruits_tuple)
      if memo_recruits and recruits != memo_recruits:
        continue
      memo_recruits = NOBODY
      self.write_memo(MemoKey.RECRUITS, recruits)
      self.choose_loyalty_missions(Team().recruit(recruits))
    self.clear_memo(MemoKey.RECRUITS)

  def choose_loyalty_missions(self, team: Team) -> None:
    # Iterate through all relevant loyalty mappings. Morinth is always loyal.
    loyalty = self.read_memo(MemoKey.LOYALTY, Ally.Morinth.value)
    while loyalty <= EVERYONE.value:
      self.loyalty = Ally(loyalty)
      # The loyalty of unrecruited allies does not matter. Avoid redundant
      # traversals by "skipping" their bits.
      if self.loyalty & RECRUITABLE & ~team.active:
        loyalty += lsb(loyalty)
        continue
      self.write_memo(MemoKey.LOYALTY, loyalty)
      self.choose_morinth(team)
      # Increment loop variable.
      loyalty += 1
    self.clear_memo(MemoKey.LOYALTY)
  
  def choose_morinth(self, team: Team) -> None:
    if not self.read_memo(MemoKey.MORINTH, False):
      self.choose_armor_upgrade(team)
    # If Samara was recruited and loyal, re-run with Morinth instead.
    # Recruiting Morinth always kills Samara.
    if Ally.Samara & team.active and self.loyal(Ally.Samara):
      self.write_memo(MemoKey.MORINTH, True)
      self.choose_armor_upgrade(copy(team).recruit(Ally.Morinth))
    self.clear_memo(MemoKey.MORINTH)

  def choose_armor_upgrade(self, team: Team) -> None:
    # If you upgrade to Silaris Armor, no one dies.
    if self.read_memo(MemoKey.ARMOR, True):
      self.choose_shield_upgrade(team)
    # Otherwise, there is a victim.
    self.write_memo(MemoKey.ARMOR, False)
    victim = self.get_victim(team.active, DP_NO_ARMOR_UPGRADE)
    self.choose_shield_upgrade(copy(team).kill(victim))
    self.clear_memo(MemoKey.ARMOR)

  def choose_shield_upgrade(self, team: Team) -> None:
    # If you upgrade to Cyclonic Shields, no one dies.
    if self.read_memo(MemoKey.SHIELD, True):
      self.choose_weapon_upgrade(team)
    # Otherwise, there is a victim, but you can affect who it is through your
    # squad selection for the battle in the cargo bay.
    self.write_memo(MemoKey.SHIELD, False)
    self.choose_cargo_bay_squad(team)
    self.clear_memo(MemoKey.SHIELD)

  def choose_cargo_bay_squad(self, team: Team) -> None:
    memo_pick = self.read_memo(MemoKey.CB_PICK, 0)
    pool = team.active
    # If you do *not* pick the #1 victim, they will die. If you pick the #1
    # victim but not the #2 victim, the #2 victim will die. If you pick both,
    # the #3 victim will die. Therefore, there are only three possible victims.
    picks: list[Ally] = []
    for pick in range(3):
      victim = self.get_victim(pool, DP_NO_SHIELD_UPGRADE)
      picks.append(victim)
      if pick >= memo_pick:
        self.write_memo(MemoKey.CB_PICK, pick)
        self.cache[CacheKey.CARGO_BAY_PICKS] = picks
        self.choose_weapon_upgrade(copy(team).kill(victim))
      # Selecting the prioritized victim(s) for your squad removes them from the
      # victim pool.
      pool &= ~victim
    self.cache.pop(CacheKey.CARGO_BAY_PICKS, None)
    self.clear_memo(MemoKey.CB_PICK)

  def choose_weapon_upgrade(self, team: Team) -> None:
    # This is a reasonable place to perform a periodic save. Based on rough
    # timing, this method is called approximately every 16 seconds or so. This
    # is not so frequent as to wear out the disk, and it is not so infrequent
    # that an unexpected shutdown would lose a lot of progress.
    self.save()

    # If you upgrade to the Thanix Cannon, no one dies.
    if self.read_memo(MemoKey.WEAPON, True):
      self.choose_tech(team)
    # Otherwise, there is a victim.
    self.write_memo(MemoKey.WEAPON, False)
    victim = self.get_victim(team.active, DP_NO_WEAPON_UPGRADE)
    self.choose_tech(copy(team).kill(victim))
    self.clear_memo(MemoKey.WEAPON)
  
  def choose_tech(self, team: Team) -> None:
    # Iterate through all selectable teammates for the tech specialist.
    cur_tech = self.read_memo(MemoKey.TECH, NOBODY)
    for tech in team.active & ~cur_tech.lt():
      self.write_memo(MemoKey.TECH, tech)
      # If the tech specialist is not loyal or ideal, they will die, regardless
      # of the leader selection.
      if not self.loyal(tech) or not (tech & IDEAL_TECHS):
        self.choose_biotic(copy(team).kill(tech))
      else:
        # Otherwise, their survival depends on the fireteam leader.
        self.choose_first_leader(team, tech)
    self.clear_memo(MemoKey.TECH)

  def choose_first_leader(self, team: Team, tech: Ally) -> None:
    # Check if we have any ideal leaders.
    ideal_leaders = team.active & ~tech & self.loyalty & IDEAL_LEADERS
    if self.read_memo(MemoKey.LEADER1, bool(ideal_leaders)):
      self.write_memo(MemoKey.LEADER1, True)
      # If the leader is loyal and ideal, the tech will be spared.
      self.choose_biotic(team)
    # Otherwise, the tech will die.
    self.write_memo(MemoKey.LEADER1, False)
    self.choose_biotic(copy(team).kill(tech))
    self.clear_memo(MemoKey.LEADER1)

  def choose_biotic(self, team: Team) -> None:
    # Iterate through all selectable teammates for the biotic specialist.
    cur_biotic = self.read_memo(MemoKey.BIOTIC, NOBODY)
    for biotic in team.active & ~cur_biotic.lt() & BIOTICS:
      self.write_memo(MemoKey.BIOTIC, biotic)
      self.choose_second_leader(team, biotic)
    self.clear_memo(MemoKey.BIOTIC)

  def choose_second_leader(self, team: Team, biotic: Ally) -> None:
    # Iterate through all selectable teammates for the second fireteam leader.
    cur_leader = self.read_memo(MemoKey.LEADER2, NOBODY)
    for leader in team.active & ~(cur_leader.lt() | biotic):
      self.write_memo(MemoKey.LEADER2, leader)
      self.choose_save_the_crew(team, biotic, leader)
    self.clear_memo(MemoKey.LEADER2)
  
  def choose_save_the_crew(self, team: Team, biotic: Ally, leader: Ally) -> None:
    #
    # FIXME: I have been unable to confirm if an escort can even be selected if
    # there are only four teammates (the minimum possible) remaining at the end
    # of the Infiltration. My current theory is that this would be disallowed
    # because it would leave only one for Shepard's squad. That is, an escort
    # literally could not be spared for the mission. Because of this, I disallow
    # it here.
    #

    # Escorting the crew is optional, if you can spare them.
    if not self.read_memo(MemoKey.CREW, False):
      self.choose_walk_squad(team, biotic, leader)
    if len(team.active) > 4:
      # Escorting the crew will save them.
      self.write_memo(MemoKey.CREW, True)
      self.choose_escort(team, biotic, leader)
    self.clear_memo(MemoKey.CREW)

  def choose_escort(self, team: Team, biotic: Ally, leader: Ally) -> None:
    # If an escort is selected, they will survive if they are loyal. Otherwise,
    # they will die.
    cur_escort = self.read_memo(MemoKey.ESCORT, NOBODY)
    for escort in team.active & ESCORTS & ~(cur_escort.lt() | biotic | leader):
      self.write_memo(MemoKey.ESCORT, escort)
      s = copy(team)
      s.spare(escort) if self.loyal(escort) else s.kill(escort)
      self.choose_walk_squad(s, biotic, leader)
    self.clear_memo(MemoKey.ESCORT)
  
  def choose_walk_squad(self, team: Team, biotic: Ally, leader: Ally) -> None:
    # If the biotic specialist is loyal and ideal, they will not get anyone on
    # your squad killed, so the squad choice does not matter.
    if self.loyal(biotic) and biotic & IDEAL_BIOTICS:
      return self.choose_final_squad(team, leader)
    # If your team is too small to merit a meaningful squad selection, there is
    # only one possible outcome.
    pool = team.active & ~(biotic | leader)
    if len(pool) < 3:
      victim = self.get_victim(pool, DP_THE_LONG_WALK)
      return self.choose_final_squad(copy(team).kill(victim), leader)
    # Otherwise, you may be able to affect who the victim is through your squad
    # selection.
    memo_unpick = self.read_memo(MemoKey.WALK_UNPICK, 0)
    self.cache[CacheKey.LONG_WALK_UNPICKS] = (unpicks := [])
    for unpick in range(min(len(pool) - 1, 3)):
      victim = self.get_victim(pool, DP_THE_LONG_WALK)
      unpicks.append(victim)
      if unpick >= memo_unpick:
        self.write_memo(MemoKey.WALK_UNPICK, unpick)
        self.choose_final_squad(copy(team).kill(victim), leader)
      # *Not* selecting the prioritized victim(s) removes them from the victim
      # pool.
      pool &= ~victim
    self.cache.pop(CacheKey.LONG_WALK_UNPICKS, None)
    self.clear_memo(MemoKey.WALK_UNPICK)

  def choose_final_squad(self, team: Team, leader: Ally) -> None:
    # The leader of the second fireteam will not die under several conditions:
    # 1. They are loyal and ideal
    # 2. They are special-cased (Miranda)
    # 3. There are fewer than four active teammates (including the leader).
    alive = self.loyal(leader) and leader & IDEAL_LEADERS
    alive = alive or leader & IMMORTAL_LEADERS or len(team.active) < 4
    if not alive:
      team = copy(team).kill(leader)
    # Iterate through all possible final squads.
    memo_squad = self.read_memo(MemoKey.FINAL_SQUAD, NOBODY)
    for squad_tuple in combinations(team.active & ~memo_squad.lt(), 2):
      squad: Ally = reduce(or_, squad_tuple)
      if memo_squad and squad != memo_squad:
        continue
      memo_squad = NOBODY
      self.write_memo(MemoKey.FINAL_SQUAD, squad)
      # The remaining active teammates will "hold the line."
      htl_mates = team.active & ~squad
      htl_toll = self.get_htl_toll(htl_mates)
      s = copy(team)
      for _ in range(htl_toll):
        victim = self.get_htl_victim(htl_mates)
        s.kill(victim)
        htl_mates &= ~victim
      # Any member of your squad that is not loyal will die.
      for squadmate in squad:
        if not self.loyal(squadmate):
          s.kill(squadmate)
      # Any active teammates at this point have survived.
      s.spare(s.active)
      self.encode_outcome(s)
    self.clear_memo(MemoKey.FINAL_SQUAD)


if __name__ == '__main__':
  dt = DecisionTree()
  dt.generate()

  # Print the number of outcomes generated so far.
  print(sum(t[0] for t in dt.outcomes.values()), 'traversals')
  print(len(dt.outcomes), 'unique outcomes')