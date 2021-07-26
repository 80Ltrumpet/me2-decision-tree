from __future__ import annotations
from enum import Enum as _Enum, auto as _auto
from functools import reduce as _reduce
from itertools import combinations as _combos
from operator import or_ as _or_
from pickle import Pickler as _Pickler, Unpickler as _Unpickler
from signal import SIGINT, signal as _signal
from typing import Any, Optional, TYPE_CHECKING, TypeVar

from .ally import *
from .bits import bits as _bits, ffs as _ffs, fsb as _fsb, mtz as _mtz
from .bits import popcount as _popcount
from .death import *
from .encdec import Decoder as _Decoder, Encoder as _Encoder
from .encdec import decode_outcome as _decode_outcome
from .encdec import encode_outcome as _encode_outcome
from .util import PeriodicTimer

def describe_outcome(encoded: int, *, full: bool = False) -> str:
  """Produces a human-readable string describing the encoded outcome.
  
  For the most verbose output, set full to True.
  """
  outcome = _decode_outcome(encoded)

  if full:
    output  = f'Survived: ({len(outcome["spared"])}) {outcome["spared"]}\n'
    output += f'Dead:     ({len(outcome["dead"])}) {outcome["dead"]}\n'
    if outcome['loyalty'] == outcome['spared']:
      output += 'Loyal:    everyone\n'
    else:
      output += f'Loyal:    {outcome["loyalty"]}\n'
    return output + f'Crew:     {"survived" if outcome["crew"] else "dead"}'
  
  output = f'{len(outcome["spared"])} survived; {len(outcome["dead"])} dead; '
  return output + f'crew {"spared" if outcome["crew"] else "dead"}.'

def describe_traversal(entry: tuple[int, tuple[int, int]]) -> str:
  """Produces a human-readable string describing the traversal encoded in the
  outcome dictionary entry."""
  # First, decode the traversal using the same variable sequence as the
  # encoding.
  decoder = _Decoder(entry[1][1])
  loyal = decoder.decode_ally_loyalty()
  upgraded_armor = decoder.decode_bool()
  upgraded_shield = decoder.decode_bool()
  upgraded_weapon = decoder.decode_bool()
  if not upgraded_shield:
    cbs_invert, cbs_picks = decoder.decode_choices()
  tech = decoder.decode_ally_index()
  has_leader1 = bool(tech & loyal & IDEAL_TECHS)
  if has_leader1:
    leader1 = decoder.decode_bool()
    ideal_leaders = decoder.decode_ideal_leaders()
  biotic = decoder.decode_ally_index()
  leader2 = decoder.decode_ally_index()
  escort = decoder.decode_ally_index()
  has_tlw_unpicks = decoder.decode_bool()
  if has_tlw_unpicks:
    tlw_invert, tlw_unpicks = decoder.decode_choices()
  final_squad = decoder.decode_squad()

  output = ''
  if upgraded_armor and upgraded_shield and upgraded_weapon:
    output += 'Upgrade everything.\n'
  elif not (upgraded_armor or upgraded_shield or upgraded_weapon):
    output += 'No Normandy upgrades.\n'
  else:
    upgrade_map = {
      'Silaris Armor': upgraded_armor,
      'Cyclonic Shields': upgraded_shield,
      'Thanix Cannon': upgraded_weapon
    }
    output += f'Upgrade: {", ".join(k for k, v in upgrade_map.items() if v)}\n'

  # Recruitment is decoded from the outcome.
  outcome = _decode_outcome(entry[0])
  everyone = outcome['spared'] | outcome['dead'] | REQUIRED
  output += f'Recruit: {everyone & OPTIONAL}\n'

  if loyal == everyone & LOYALTY_MASK:
    output += 'Do all loyalty missions.\n'
  elif not loyal:
    output += 'Do no loyalty missions.\n'
  else:
    output += f'Loyalty Missions: {loyal}\n'
  
  if not upgraded_shield:
    output += 'For the cargo bay squad, '
    cbs_take = _reduce(_or_,
      cbs_picks[:-1] if cbs_invert else cbs_picks, NOBODY)
    cbs_leave = cbs_picks[-1] if cbs_invert else NOBODY
    if cbs_take:
      output += f'pick {cbs_take}'
      if cbs_leave:
        output += ' and '
    if cbs_leave:
      output += f'make sure to leave {cbs_leave} behind'
    output += '.\n'
  
  output += f'Choose {tech} as the tech specialist.\n'
  if has_leader1:
    output += 'Choose '
    if not leader1:
      output += 'anyone except '
    output += f'{ideal_leaders.conj("or")} to lead the second fireteam.\n'
  else:
    output += 'The second fireteam leader does not matter.\n'

  output += f'Choose {biotic} as the biotic specialist.\n'
  output += f'Choose {leader2} to lead the diversion team.\n'
  if escort:
    output += f'Send {escort} to escort the crew.\n'
  else:
    output += 'Do not send anyone to escort the crew.\n'
  if has_tlw_unpicks:
    output += 'For the squad in the biotic shield, '
    tlw_take = tlw_unpicks[-1] if tlw_invert else NOBODY
    tlw_leave = _reduce(_or_,
      tlw_unpicks[:-1] if tlw_invert else tlw_unpicks, NOBODY)
    if tlw_take:
      output += f'pick {tlw_take}'
      if tlw_leave:
        output += ' and '
    if tlw_leave:
      output += f'make sure to leave {tlw_leave} behind'
    output += '.\n'

  output += f'Pick {final_squad} for your final squad.\n'
  return output


# Static analysis does not do so well with mixin-esque classes. Since Team does
# not explicitly declare its attributes, we have to special-case its definition
# for type-checking to avoid "unfair" errors.
if TYPE_CHECKING:
  class MutableTeam:
    active = REQUIRED.value
    dead = 0
    spared = 0
  _TeamBase = MutableTeam
else:
  _TeamBase = object

class Team(_TeamBase):
  """Team state tracker
  
  This class is immutable to make it "stack-friendly." Operative methods always
  return a new instance.
  """
  __slots__ = ['active', 'dead', 'spared']

  def __init__(self,
               active: int = REQUIRED.value,
               dead: int = 0,
               spared: int = 0) -> None:
    """Initializes team state."""
    super().__setattr__('active', active)
    super().__setattr__('dead', dead)
    super().__setattr__('spared', spared)

  def __setattr__(self, name: str, value: Any) -> None:
    raise TypeError("'Team' object does not support attribute assignment")
  
  def kill(self, ally: int) -> Team:
    """Returns a new Team where the specified ally is dead."""
    return Team(self.active & ~ally, self.dead | ally, self.spared)

  def spare(self, ally: int) -> Team:
    """Returns a new Team where the specified ally is spared."""
    return Team(self.active & ~ally, self.dead, self.spared | ally)

  def kill_and_spare_active(self, ally: int) -> Team:
    """Returns a new Team where the specified ally is dead and all active allies
    are spared."""
    return Team(0, self.dead | ally, self.spared | (self.active & ~ally))

  def recruit(self, ally: int) -> Team:
    """Returns a new Team where the specified ally is active."""
    active = self.active | ally
    dead = self.dead
    # To add Morinth to the team, Samara must be dead.
    if Ally.Morinth.value & ally:
      active &= ~Ally.Samara.value
      dead |= Ally.Samara.value
    return Team(active, dead, self.spared)


class MemoKey(_Enum):
  N_OPT = _auto()
  RECRUITS = _auto()
  LOYALTY = _auto()
  MORINTH = _auto()
  ARMOR = _auto()
  SHIELD = _auto()
  CB_PICK = _auto()
  WEAPON = _auto()
  TECH = _auto()
  LEADER1 = _auto()
  BIOTIC = _auto()
  LEADER2 = _auto()
  CREW = _auto()
  ESCORT = _auto()
  WALK_UNPICK = _auto()
  FINAL_SQUAD = _auto()


class CacheKey(_Enum):
  CARGO_BAY_PICKS = _auto()
  IDEAL_LEADERS = _auto()
  LONG_WALK_UNPICKS = _auto()


class _DecisionTreePauseException(Exception):
  """Custom exception type for pausing execution of the decision tree."""
  pass


# Used for generic type annotations.
_T = TypeVar('_T')

# Interval in seconds between periodic saves.
_SAVE_INTERVAL = 5 * 60

class DecisionTree:
  """Generates outcomes and traversals for Mass Effect 2's suicide mission.
  
  This class performs a depth-first traversal of all possible combinations of
  decisions that affect the survival of allies in Mass Effect 2's final
  mission sequence. This will generate a dictionary of all possible outcomes
  mapped to the decision sequences that produce them.
  
  Due to the highly recursive nature of the algorithm, memory usage is a
  concern. To reduce it somewhat, decision sequences and outcomes are encoded
  into a compact format for storage.
  """
  def __init__(self, file_path: str):
    """Constructs a decision tree and optionally loads data from the file at the
    given file_path."""
    if not file_path:
      raise ValueError('A decision tree file path must be provided')
    # Similar to the memo, but not persistent.
    self.cache: dict[CacheKey, Any] = {}
    self.file_path = file_path
    self.loyal = 0
    self.memo: dict[str, Any] = {}
    self.needs_save = False
    self.outcomes: dict[int, tuple[int, int]] = {}
    self.pausing = False
    # Used for marking which keys from the memo have already been read.
    self.spent_memo_keys: set[MemoKey] = set()
    self.load()

  #
  # Outcome Encoding
  #

  def record_outcome(self, team: Team) -> None:
    """Encodes the outcome based on the final state of the team and adds it to
    the outcome dictionary with a 2-tuple containing the number of traversals
    resulting in that outcome and an encoding of the last such traversal."""
    # The encoded outcome is 34 bits wide.
    outcome = _encode_outcome(
      spared = team.spared,
      dead = team.dead,
      loyalty = team.spared & self.loyal,
      crew = self.memo.get(MemoKey.CREW.name, False)
    )

    # The bit-width of the encoded traversal is variable. (min, max) = (40, 62)
    encoder = _Encoder()
    encoder.encode_ally_loyalty(self.loyal & (team.spared | team.dead))
    encoder.encode_bool(self.memo.get(MemoKey.ARMOR.name, True))
    encoder.encode_bool((shield := self.memo.get(MemoKey.SHIELD.name, True)))
    encoder.encode_bool(self.memo.get(MemoKey.WEAPON.name, True))
    if not shield:
      # This cache key is mandatory if the shield is not upgraded.
      encoder.encode_choices(self.cache[CacheKey.CARGO_BAY_PICKS])
    encoder.encode_ally_index(_ffs(self.memo[MemoKey.TECH.name]) + 1)
    leader1: Optional[bool] = self.memo.get(MemoKey.LEADER1.name, None)
    if leader1 is not None:
      encoder.encode_bool(leader1)
      # This cache key is mandatory if an ideal leader is selected.
      encoder.encode_ideal_leaders(self.cache[CacheKey.IDEAL_LEADERS])
    encoder.encode_ally_index(_ffs(self.memo[MemoKey.BIOTIC.name]) + 1)
    encoder.encode_ally_index(_ffs(self.memo[MemoKey.LEADER2.name]) + 1)
    encoder.encode_ally_index(_ffs(self.memo.get(MemoKey.ESCORT.name, 0)) + 1)
    walk_unpick = self.memo.get(MemoKey.WALK_UNPICK.name, None) is not None
    encoder.encode_bool(walk_unpick)
    if walk_unpick:
      # This cache key is mandatory if the biotic is not loyal and ideal and a
      # meaningful squad selection is possible.
      encoder.encode_choices(self.cache[CacheKey.LONG_WALK_UNPICKS])
    encoder.encode_squad(self.memo.get(MemoKey.FINAL_SQUAD.name, 0))
    traversal = encoder.result
    
    # Replace the outcome tuple.
    traversal_count = self.outcomes.get(outcome, (0, 0))[0] + 1
    self.outcomes[outcome] = (traversal_count, traversal)

  #
  # Memo
  #
  # Although the MemoKey enumeration members are used as arguments to the
  # following methods, their names are stored as the keys for optimal pickling.
  #

  def read_memo(self, key: MemoKey, default: _T) -> _T:
    """Gets the value of the requested memo key on the first call.
    
    On subsequent calls or if the key is not in the memo, returns default.
    """
    if key in self.spent_memo_keys:
      return default
    self.spent_memo_keys.add(key)
    return self.memo.get(key.name, default)
  
  def write_memo(self, key: MemoKey, value: Any) -> None:
    """Sets the value for the requested memo key and checks if the user
    requested a pause or if a periodic save was requested."""
    self.memo[key.name] = value
    if self.pausing:
      raise _DecisionTreePauseException()
    if self.needs_save:
      self.save()
      self.needs_save = False

  def clear_memo(self, key: MemoKey) -> None:
    """Deletes a key from the memo, whether or not it exists."""
    self.memo.pop(key.name, None)
  
  #
  # Persistence
  #

  def save(self) -> None:
    """Writes memo and outcome data to a file."""
    with open(self.file_path, 'wb') as datafile:
      pickler = _Pickler(datafile)
      pickler.dump(self.memo)
      pickler.dump(self.outcomes)

  def load(self) -> None:
    """Reads memo and outcome data from a file."""
    try:
      with open(self.file_path, 'rb') as datafile:
        unpickler = _Unpickler(datafile)
        self.memo = unpickler.load()
        self.outcomes = unpickler.load()
    except FileNotFoundError:
      pass
  
  #
  # Runtime
  #

  def is_complete(self) -> bool:
    """Checks if the decision tree has exhausted all possible traversals."""
    return self.memo.get(MemoKey.N_OPT.name, None) == 0

  def generate(self) -> None:
    """Generates decision tree outcomes."""
    # Set up a timer to periodically save progress.
    def request_save() -> None:
      self.needs_save = True
    saver = PeriodicTimer(_SAVE_INTERVAL, request_save)
    saver.start()
    # Pressing Ctrl-C gracefully pauses the operation.
    def handle_sigint(*_) -> None:
      self.pausing = True
    sigint_handler = _signal(SIGINT, handle_sigint)
    try:
      self.choose_recruitment()
    except _DecisionTreePauseException:
      pass
    finally:
      self.save()
    # Restore the original SIGINT handler.
    _signal(SIGINT, sigint_handler)
    saver.cancel()

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
    memo_recruits = self.read_memo(MemoKey.RECRUITS, 0)
    remaining_recruits = RECRUITABLE.value & ~_mtz(memo_recruits)
    for recruits_tuple in _combos(_bits(remaining_recruits), n):
      recruits: int = _reduce(_or_, recruits_tuple)
      if memo_recruits and recruits != memo_recruits:
        continue
      memo_recruits = 0
      self.write_memo(MemoKey.RECRUITS, recruits)
      self.choose_loyalty_missions(Team().recruit(recruits))
    self.clear_memo(MemoKey.RECRUITS)

  def choose_loyalty_missions(self, team: Team) -> None:
    # Iterate through all relevant loyalty mappings. Morinth is always loyal.
    loyalty = self.read_memo(MemoKey.LOYALTY, Ally.Morinth.value)
    while loyalty <= EVERYONE.value:
      self.loyal = loyalty
      # The loyalty of unrecruited allies does not matter. Avoid redundant
      # traversals by "skipping" their bits.
      if self.loyal & LOYALTY_MASK.value & ~team.active:
        loyalty += _fsb(loyalty)
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
    if Ally.Samara.value & team.active & self.loyal:
      self.write_memo(MemoKey.MORINTH, True)
      self.choose_armor_upgrade(team.recruit(Ally.Morinth.value))
    self.clear_memo(MemoKey.MORINTH)

  def choose_armor_upgrade(self, team: Team) -> None:
    # If you upgrade to Silaris Armor, no one dies.
    if self.read_memo(MemoKey.ARMOR, True):
      self.choose_shield_upgrade(team)
    # Otherwise, there is a victim.
    self.write_memo(MemoKey.ARMOR, False)
    victim = get_victim(team.active, DP_NO_ARMOR_UPGRADE)
    self.choose_shield_upgrade(team.kill(victim))
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
    picks: list[int] = []
    for pick in range(3):
      victim = get_victim(pool, DP_NO_SHIELD_UPGRADE)
      picks.append(victim)
      if pick >= memo_pick:
        self.write_memo(MemoKey.CB_PICK, pick)
        self.cache[CacheKey.CARGO_BAY_PICKS] = picks
        self.choose_weapon_upgrade(team.kill(victim))
      # Selecting the prioritized victim(s) for your squad removes them from the
      # victim pool.
      pool &= ~victim
    del self.cache[CacheKey.CARGO_BAY_PICKS]
    self.clear_memo(MemoKey.CB_PICK)

  def choose_weapon_upgrade(self, team: Team) -> None:
    # If you upgrade to the Thanix Cannon, no one dies.
    if self.read_memo(MemoKey.WEAPON, True):
      self.choose_tech(team)
    # Otherwise, there is a victim.
    self.write_memo(MemoKey.WEAPON, False)
    victim = get_victim(team.active, DP_NO_WEAPON_UPGRADE)
    self.choose_tech(team.kill(victim))
    self.clear_memo(MemoKey.WEAPON)
  
  def choose_tech(self, team: Team) -> None:
    # Iterate through all selectable teammates for the tech specialist.
    cur_tech = self.read_memo(MemoKey.TECH, 0)
    for tech in _bits(team.active & TECHS.value & ~_mtz(cur_tech)):
      self.write_memo(MemoKey.TECH, tech)
      # If the tech specialist is loyal and ideal, their survival depends on the
      # first fireteam leader.
      if tech & self.loyal & IDEAL_TECHS.value:
        self.choose_first_leader(team, tech)
      else:
        # Otherwise, they will die. The first fireteam leader does not matter.
        self.choose_biotic(team.kill(tech))
    self.clear_memo(MemoKey.TECH)

  def choose_first_leader(self, team: Team, tech: int) -> None:
    # Check if we have any ideal leaders.
    ideal_leaders = team.active & ~tech & self.loyal & IDEAL_LEADERS.value
    self.cache[CacheKey.IDEAL_LEADERS] = ideal_leaders
    if self.read_memo(MemoKey.LEADER1, bool(ideal_leaders)):
      self.write_memo(MemoKey.LEADER1, True)
      # If the leader is loyal and ideal, the tech will be spared.
      self.choose_biotic(team)
    # Otherwise, the tech will die.
    self.write_memo(MemoKey.LEADER1, False)
    self.choose_biotic(team.kill(tech))
    del self.cache[CacheKey.IDEAL_LEADERS]
    self.clear_memo(MemoKey.LEADER1)

  def choose_biotic(self, team: Team) -> None:
    # Iterate through all selectable teammates for the biotic specialist.
    cur_biotic = self.read_memo(MemoKey.BIOTIC, 0)
    for biotic in _bits(team.active & BIOTICS.value & ~_mtz(cur_biotic)):
      self.write_memo(MemoKey.BIOTIC, biotic)
      self.choose_second_leader(team, biotic)
    self.clear_memo(MemoKey.BIOTIC)

  def choose_second_leader(self, team: Team, biotic: int) -> None:
    # Iterate through all selectable teammates for the second fireteam leader.
    cur_leader = self.read_memo(MemoKey.LEADER2, 0)
    for leader in _bits(team.active & ~(biotic | _mtz(cur_leader))):
      self.write_memo(MemoKey.LEADER2, leader)
      self.choose_save_the_crew(team, biotic, leader)
    self.clear_memo(MemoKey.LEADER2)
  
  def choose_save_the_crew(self, team: Team, biotic: int, leader: int) -> None:
    # Escorting the crew is optional, if you can spare them.
    # NOTE: If only four teammates (the minimum possible) remain at this point,
    # then an escort cannot be selected, since Shepard must have two squadmates
    # for The Long Walk.
    if not self.read_memo(MemoKey.CREW, False):
      self.choose_walk_squad(team, biotic, leader)
    if _popcount(team.active) > 4:
      # Escorting the crew will save them.
      self.write_memo(MemoKey.CREW, True)
      self.choose_escort(team, biotic, leader)
    self.clear_memo(MemoKey.CREW)

  def choose_escort(self, team: Team, biotic: int, leader: int) -> None:
    # If an escort is selected, they will be spared if they are loyal.
    # Otherwise, they will die.
    cur_escort = self.read_memo(MemoKey.ESCORT, 0)
    remaining_escorts = team.active & ESCORTS.value
    remaining_escorts &= ~(biotic | leader | _mtz(cur_escort))
    for escort in _bits(remaining_escorts):
      self.write_memo(MemoKey.ESCORT, escort)
      t = team.spare(escort) if escort & self.loyal else team.kill(escort)
      self.choose_walk_squad(t, biotic, leader)
    self.clear_memo(MemoKey.ESCORT)
  
  def choose_walk_squad(self, team: Team, biotic: int, leader: int) -> None:
    # If the biotic specialist is loyal and ideal, they will not get anyone on
    # your squad killed, so the squad choice does not matter.
    if biotic & self.loyal & IDEAL_BIOTICS.value:
      return self.choose_final_squad(team, leader)
    # If your team is too small to merit a meaningful squad selection, there is
    # only one possible outcome.
    pool = team.active & ~(biotic | leader)
    if _popcount(pool) < 3:
      victim = get_victim(pool, DP_THE_LONG_WALK)
      return self.choose_final_squad(team.kill(victim), leader)
    # Otherwise, you may be able to affect who the victim is through your squad
    # selection.
    memo_unpick = self.read_memo(MemoKey.WALK_UNPICK, 0)
    self.cache[CacheKey.LONG_WALK_UNPICKS] = (unpicks := [])
    for unpick in range(min(_popcount(pool) - 1, 3)):
      victim = get_victim(pool, DP_THE_LONG_WALK)
      unpicks.append(victim)
      if unpick >= memo_unpick:
        self.write_memo(MemoKey.WALK_UNPICK, unpick)
        self.choose_final_squad(team.kill(victim), leader)
      # *Not* selecting the prioritized victim(s) removes them from the victim
      # pool.
      pool &= ~victim
    del self.cache[CacheKey.LONG_WALK_UNPICKS]
    self.clear_memo(MemoKey.WALK_UNPICK)

  def choose_final_squad(self, team: Team, leader: int) -> None:
    # The leader of the second fireteam will not die under several conditions:
    # 1. They are loyal and ideal
    # 2. They are special-cased (Miranda)
    # 3. There are fewer than four active teammates (including the leader).
    alive = bool(leader & self.loyal & IDEAL_LEADERS.value)
    alive = alive or bool(leader & IMMORTAL_LEADERS.value)
    if not (alive or _popcount(team.active) < 4):
      team = team.kill(leader)
    # Iterate through all possible final squads.
    memo_squad = self.read_memo(MemoKey.FINAL_SQUAD, 0)
    for squad_tuple in _combos(_bits(team.active & ~_mtz(memo_squad)), 2):
      squad: int = _reduce(_or_, squad_tuple)
      if memo_squad and squad != memo_squad:
        continue
      memo_squad = 0
      self.write_memo(MemoKey.FINAL_SQUAD, squad)
      # The remaining active teammates form the defense team.
      defense_team = team.active & ~squad
      death_toll = get_defense_toll(defense_team, self.loyal)
      victims = 0
      for _ in range(death_toll):
        victims |= get_defense_victim(defense_team & ~victims, self.loyal)
      # Any member of your squad that is not loyal will die.
      victims |= squad & ~self.loyal
      # Any active teammates at this point have survived.
      self.record_outcome(team.kill_and_spare_active(victims))
    self.clear_memo(MemoKey.FINAL_SQUAD)