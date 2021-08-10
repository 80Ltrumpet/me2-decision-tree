from __future__ import annotations
import enum
from functools import reduce
from itertools import combinations
from operator import or_ as op_or
import pickle
from typing import Any, Optional

from .ally import *
from . import bits, death, encdec, util

def describe_outcome(encoded: int, *, brief: bool = False) -> str:
  """Produces a human-readable string describing the encoded outcome.
  
  For brief output, set brief to True.
  """
  spared, loyalty, crew = encdec.decode_outcome(encoded)
  ally_count = len(spared)

  if brief:
    x_allies = f'{ally_count} all{"ies" if ally_count != 1 else "y"}'
    and_the_crew = ' and the crew ' if crew else ' '
    return f'{x_allies}{and_the_crew}survived.'

  output  = f'Survived: ({ally_count}) {spared}\n'
  output += f'Loyal:    {loyalty}\n'
  return output + f'Crew:     {"survived" if crew else "dead"}'


def describe_traversal(traversal: int) -> str:
  """Produces a human-readable string describing the encoded traversal."""
  # First, decode the traversal using the same variable sequence as the
  # encoding.
  decoder = encdec.Decoder(traversal)
  recruits = decoder.decode_ally_optional()
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

  output += f'Recruit: {recruits}\n'

  if loyal == (recruits | REQUIRED) & LOYALTY_MASK:
    output += 'Do all loyalty missions.\n'
  elif not loyal:
    output += 'Do no loyalty missions.\n'
  else:
    output += f'Loyalty Missions: {loyal}\n'
  
  if not upgraded_shield:
    output += 'For the cargo bay squad, '
    cbs_take = reduce(op_or,
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
    tlw_leave = reduce(op_or,
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


class Checkpoint(enum.Enum):
  N_OPT = enum.auto()
  RECRUITS = enum.auto()
  LOYALTY = enum.auto()
  MORINTH = enum.auto()
  ARMOR = enum.auto()
  SHIELD = enum.auto()
  CB_PICK = enum.auto()
  WEAPON = enum.auto()
  TECH = enum.auto()
  LEADER1 = enum.auto()
  BIOTIC = enum.auto()
  LEADER2 = enum.auto()
  CREW = enum.auto()
  ESCORT = enum.auto()
  WALK_UNPICK = enum.auto()
  FINAL_SQUAD = enum.auto()


class CacheKey(enum.Enum):
  CARGO_BAY_PICKS = enum.auto()
  IDEAL_LEADERS = enum.auto()
  LONG_WALK_UNPICKS = enum.auto()


class DecisionTreePauseException(Exception):
  """Custom exception type for pausing execution of the decision tree."""
  pass


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
    # Stores checkpoint data that is necessary for traversal encoding but not
    # ideal for restoring iteration state.
    self.cache: dict[CacheKey, Any] = {}
    self.file_path = file_path
    self.loyal = 0
    self.checkpoints: dict[Checkpoint, Any] = {}
    self.needs_save = False
    # The first value in the tuple is the number of traversals that achieve the
    # outcome (key), and the second value is an encoded traversal that achieves
    # the outcome.
    self.outcomes: dict[int, tuple[int, int]] = {}
    self.pausing = False
    self.load()

  #
  # Outcome Encoding
  #

  def record_outcome(self, team: int):
    """Encodes the outcome based on the final state of the team and adds it to
    the outcome dictionary with a 2-tuple containing the number of traversals
    resulting in that outcome and an encoding of the last such traversal."""
    # Check if the escort survived.
    escort = self.checkpoints.get(Checkpoint.ESCORT, 0)
    if escort & self.loyal:
      team |= escort

    # The encoded outcome is 26 bits long.
    outcome = encdec.encode_outcome(
      spared = team,
      loyalty = team & self.loyal,
      crew = self.checkpoints.get(Checkpoint.CREW, False)
    )

    # The bit-width of the encoded traversal is variable. (min, max) = (48, 70)
    encoder = encdec.Encoder()
    encoder.encode_ally_optional(self.checkpoints[Checkpoint.RECRUITS])
    encoder.encode_ally_loyalty(self.loyal)
    encoder.encode_bool(self.checkpoints.get(Checkpoint.ARMOR, True))
    shield = self.checkpoints.get(Checkpoint.SHIELD, True)
    encoder.encode_bool(shield)
    encoder.encode_bool(self.checkpoints.get(Checkpoint.WEAPON, True))
    if not shield:
      # This cache key is mandatory if the shield is not upgraded.
      encoder.encode_choices(self.cache[CacheKey.CARGO_BAY_PICKS])
    encoder.encode_ally_index(bits.ffs(self.checkpoints[Checkpoint.TECH]) + 1)
    leader1: Optional[bool] = self.checkpoints.get(Checkpoint.LEADER1, None)
    if leader1 is not None:
      encoder.encode_bool(leader1)
      # This cache key is mandatory if a non-ideal tech is selected.
      encoder.encode_ideal_leaders(self.cache[CacheKey.IDEAL_LEADERS])
    encoder.encode_ally_index(bits.ffs(self.checkpoints[Checkpoint.BIOTIC]) + 1)
    encoder.encode_ally_index(
      bits.ffs(self.checkpoints[Checkpoint.LEADER2]) + 1)
    encoder.encode_ally_index(bits.ffs(escort) + 1)
    walk_unpick = self.checkpoints.get(Checkpoint.WALK_UNPICK, None) is not None
    encoder.encode_bool(walk_unpick)
    if walk_unpick:
      # This cache key is mandatory if the biotic is not loyal and ideal and a
      # meaningful squad selection is possible.
      encoder.encode_choices(self.cache[CacheKey.LONG_WALK_UNPICKS])
    encoder.encode_squad(self.checkpoints.get(Checkpoint.FINAL_SQUAD, 0))
    traversal = encoder.result
    
    # Replace the outcome tuple.
    traversal_count = self.outcomes.get(outcome, (0, 0))[0] + 1
    self.outcomes[outcome] = (traversal_count, traversal)
  
  #
  # Persistence
  #

  def request_save(self):
    self.needs_save = True

  def set_checkpoint(self, key: Checkpoint, value: Any):
    """Sets the value for the requested checkpoint and checks if the user
    requested a pause or if a periodic save was requested."""
    self.checkpoints[key] = value
    if self.pausing:
      raise DecisionTreePauseException()
    if self.needs_save:
      self.save()
      self.needs_save = False

  def save(self):
    """Writes checkpoints and outcome data to a file."""
    with open(self.file_path, 'wb') as datafile:
      pickler = pickle.Pickler(datafile)
      pickler.dump(self.checkpoints)
      pickler.dump(self.outcomes)

  def load(self):
    """Reads checkpoints and outcome data from a file."""
    try:
      with open(self.file_path, 'rb') as datafile:
        unpickler = pickle.Unpickler(datafile)
        self.checkpoints = unpickler.load()
        self.outcomes = unpickler.load()
    except FileNotFoundError:
      pass
  
  #
  # Runtime
  #

  def pause(self, *_: Any):
    """Requests a pause in the decision tree generation.
    
    Ignores any additional arguments so that it can be used as a signal handler.
    """
    self.pausing = True

  def is_complete(self) -> bool:
    """Checks if the decision tree has exhausted all possible traversals."""
    return self.checkpoints.get(Checkpoint.N_OPT, None) == 0

  def generate(self):
    """Generates decision tree outcomes.
    
    If this is called in the main thread, it temporarily installs a SIGINT
    handler to gracefully pause the operation and save as much progress as
    possible. This method can also safely be called in a child thread, and
    calling pause() will ensure the thread is joinable.
    """
    if self.is_complete():
      return
    # Pressing Ctrl-C gracefully pauses the operation.
    with util.SigintHandler(self.pause):
      # Set up a timer to periodically save progress.
      with util.PeriodicTimer(_SAVE_INTERVAL, self.request_save):
        # Start generating the decision tree.
        try:
          self._choose_recruitment()
        except DecisionTreePauseException:
          pass  # Graceful pause
        finally:
          self.save()

  #
  # Private Decision Methods
  #

  def _choose_recruitment(self):
    # At least three optional allies must be recruited to finish the game.
    n_start = self.checkpoints.get(Checkpoint.N_OPT, 3)
    if n_start == 0:
      return
    for n in range(n_start, len(RECRUITABLE) + 1):
      self.set_checkpoint(Checkpoint.N_OPT, n)
      self._choose_recruits(n)
    # This signals that all outcomes have been generated.
    self.set_checkpoint(Checkpoint.N_OPT, 0)

  def _choose_recruits(self, n: int):
    # Iterate through all possible combinations of optional recruitment.
    ckpt_recruits = self.checkpoints.get(Checkpoint.RECRUITS, 0)
    remaining_recruits = RECRUITABLE.value & ~bits.mtz(ckpt_recruits)
    for recruits_tuple in combinations(bits.bits(remaining_recruits), n):
      recruits: int = reduce(op_or, recruits_tuple)
      if ckpt_recruits and recruits != ckpt_recruits:
        continue
      ckpt_recruits = 0
      self.set_checkpoint(Checkpoint.RECRUITS, recruits)
      self._choose_loyalty_missions(recruits | REQUIRED.value)
    del self.checkpoints[Checkpoint.RECRUITS]

  def _choose_loyalty_missions(self, team: int):
    # Iterate through all relevant loyalty mappings. Morinth is always loyal.
    loyalty = self.checkpoints.get(Checkpoint.LOYALTY, Ally.Morinth.value)
    while loyalty <= EVERYONE.value:
      self.loyal = loyalty
      # The loyalty of unrecruited allies does not matter. Avoid redundant
      # traversals by "skipping" their bits.
      if self.loyal & LOYALTY_MASK.value & ~team:
        loyalty += bits.fsb(loyalty)
        continue
      self.set_checkpoint(Checkpoint.LOYALTY, loyalty)
      self._choose_morinth(team)
      # Increment loop variable.
      loyalty += 1
    del self.checkpoints[Checkpoint.LOYALTY]
  
  def _choose_morinth(self, team: int):
    if not self.checkpoints.get(Checkpoint.MORINTH, False):
      self._choose_armor_upgrade(team)
    # If Samara was recruited and loyal, re-run with Morinth instead.
    # Recruiting Morinth always kills Samara.
    if Ally.Samara.value & team & self.loyal:
      self.set_checkpoint(Checkpoint.MORINTH, True)
      self._choose_armor_upgrade(team | Ally.Morinth.value & ~Ally.Samara.value)
    self.checkpoints.pop(Checkpoint.MORINTH, None)

  def _choose_armor_upgrade(self, team: int):
    # If you upgrade to Silaris Armor, no one dies.
    if self.checkpoints.get(Checkpoint.ARMOR, True):
      self._choose_shield_upgrade(team)
    # Otherwise, there is a victim.
    self.set_checkpoint(Checkpoint.ARMOR, False)
    victim = death.get_victim(team, death.DP_NO_ARMOR_UPGRADE)
    self._choose_shield_upgrade(team & ~victim)
    del self.checkpoints[Checkpoint.ARMOR]

  def _choose_shield_upgrade(self, team: int):
    # If you upgrade to Cyclonic Shields, no one dies.
    if self.checkpoints.get(Checkpoint.SHIELD, True):
      self._choose_weapon_upgrade(team)
    # Otherwise, there is a victim, but you can affect who it is through your
    # squad selection for the battle in the cargo bay.
    self.set_checkpoint(Checkpoint.SHIELD, False)
    self._choose_cargo_bay_squad(team)
    del self.checkpoints[Checkpoint.SHIELD]

  def _choose_cargo_bay_squad(self, team: int):
    ckpt_pick = self.checkpoints.get(Checkpoint.CB_PICK, 0)
    # If you do *not* pick the #1 victim, they will die. If you pick the #1
    # victim but not the #2 victim, the #2 victim will die. If you pick both,
    # the #3 victim will die. Therefore, there are only three possible victims.
    victim_pool = team
    picks: list[int] = []
    for pick in range(3):
      victim = death.get_victim(victim_pool, death.DP_NO_SHIELD_UPGRADE)
      picks.append(victim)
      if pick >= ckpt_pick:
        self.set_checkpoint(Checkpoint.CB_PICK, pick)
        self.cache[CacheKey.CARGO_BAY_PICKS] = picks
        self._choose_weapon_upgrade(team & ~victim)
      # Selecting the prioritized victim(s) for your squad removes them from the
      # victim pool.
      victim_pool &= ~victim
    del self.cache[CacheKey.CARGO_BAY_PICKS]
    del self.checkpoints[Checkpoint.CB_PICK]

  def _choose_weapon_upgrade(self, team: int):
    # If you upgrade to the Thanix Cannon, no one dies.
    if self.checkpoints.get(Checkpoint.WEAPON, True):
      self._choose_tech(team)
    # Otherwise, there is a victim.
    self.set_checkpoint(Checkpoint.WEAPON, False)
    victim = death.get_victim(team, death.DP_NO_WEAPON_UPGRADE)
    self._choose_tech(team & ~victim)
    del self.checkpoints[Checkpoint.WEAPON]
  
  def _choose_tech(self, team: int):
    # Iterate through all selectable teammates for the tech specialist.
    cur_tech = self.checkpoints.get(Checkpoint.TECH, 0)
    for tech in bits.bits(team & TECHS.value & ~bits.mtz(cur_tech)):
      self.set_checkpoint(Checkpoint.TECH, tech)
      # If the tech specialist is loyal and ideal, their survival depends on the
      # first fireteam leader.
      if tech & self.loyal & IDEAL_TECHS.value:
        self._choose_first_leader(team, tech)
      else:
        # Otherwise, they will die. The first fireteam leader does not matter.
        self._choose_biotic(team & ~tech)
    del self.checkpoints[Checkpoint.TECH]

  def _choose_first_leader(self, team: int, tech: int):
    # Check if we have any ideal leaders.
    ideal_leaders = team & ~tech & self.loyal & IDEAL_LEADERS.value
    self.cache[CacheKey.IDEAL_LEADERS] = ideal_leaders
    if self.checkpoints.get(Checkpoint.LEADER1, bool(ideal_leaders)):
      self.set_checkpoint(Checkpoint.LEADER1, True)
      # If the leader is loyal and ideal, the tech will be spared.
      self._choose_biotic(team)
    # Otherwise, the tech will die.
    self.set_checkpoint(Checkpoint.LEADER1, False)
    self._choose_biotic(team & ~tech)
    del self.cache[CacheKey.IDEAL_LEADERS]
    del self.checkpoints[Checkpoint.LEADER1]

  def _choose_biotic(self, team: int):
    # Iterate through all selectable teammates for the biotic specialist.
    cur_biotic = self.checkpoints.get(Checkpoint.BIOTIC, 0)
    for biotic in bits.bits(team & BIOTICS.value & ~bits.mtz(cur_biotic)):
      self.set_checkpoint(Checkpoint.BIOTIC, biotic)
      self._choose_second_leader(team, biotic)
    del self.checkpoints[Checkpoint.BIOTIC]

  def _choose_second_leader(self, team: int, biotic: int):
    # Iterate through all selectable teammates for the second fireteam leader.
    cur_leader = self.checkpoints.get(Checkpoint.LEADER2, 0)
    for leader in bits.bits(team & ~(biotic | bits.mtz(cur_leader))):
      self.set_checkpoint(Checkpoint.LEADER2, leader)
      self._choose_save_the_crew(team, biotic, leader)
    del self.checkpoints[Checkpoint.LEADER2]
  
  def _choose_save_the_crew(self, team: int, biotic: int, leader: int):
    # Escorting the crew is optional, if you can spare them.
    # NOTE: If only four teammates (the minimum possible) remain at this point,
    # then an escort cannot be selected, since Shepard must have two squadmates
    # for The Long Walk.
    if not self.checkpoints.get(Checkpoint.CREW, False):
      self._choose_walk_squad(team, biotic, leader)
    if bits.popcount(team) > 4:
      # Escorting the crew will save them.
      self.set_checkpoint(Checkpoint.CREW, True)
      self._choose_escort(team, biotic, leader)
    self.checkpoints.pop(Checkpoint.CREW, None)

  def _choose_escort(self, team: int, biotic: int, leader: int):
    # If an escort is selected, they will be spared if they are loyal.
    # Otherwise, they will die.
    cur_escort = self.checkpoints.get(Checkpoint.ESCORT, 0)
    remaining_escorts = team & ESCORTS.value
    remaining_escorts &= ~(biotic | leader | bits.mtz(cur_escort))
    for escort in bits.bits(remaining_escorts):
      self.set_checkpoint(Checkpoint.ESCORT, escort)
      # The escort is removed from the team, but they survive if they are loyal.
      # That logic is handled in record_outcome().
      self._choose_walk_squad(team & ~escort, biotic, leader)
    del self.checkpoints[Checkpoint.ESCORT]
  
  def _choose_walk_squad(self, team: int, biotic: int, leader: int):
    # If the biotic specialist is loyal and ideal, they will not get anyone on
    # your squad killed, so the squad choice does not matter.
    if biotic & self.loyal & IDEAL_BIOTICS.value:
      return self._choose_final_squad(team, leader)
    # If your team is too small to merit a meaningful squad selection, there is
    # only one possible outcome.
    victim_pool = team & ~(biotic | leader)
    if bits.popcount(victim_pool) < 3:
      victim = death.get_victim(victim_pool, death.DP_THE_LONG_WALK)
      return self._choose_final_squad(team & ~victim, leader)
    # Otherwise, you may be able to affect who the victim is through your squad
    # selection.
    ckpt_unpick = self.checkpoints.get(Checkpoint.WALK_UNPICK, 0)
    self.cache[CacheKey.LONG_WALK_UNPICKS] = (unpicks := [])
    for unpick in range(min(bits.popcount(victim_pool) - 1, 3)):
      victim = death.get_victim(victim_pool, death.DP_THE_LONG_WALK)
      unpicks.append(victim)
      if unpick >= ckpt_unpick:
        self.set_checkpoint(Checkpoint.WALK_UNPICK, unpick)
        self._choose_final_squad(team & ~victim, leader)
      # *Not* selecting the prioritized victim(s) removes them from the victim
      # pool.
      victim_pool &= ~victim
    del self.cache[CacheKey.LONG_WALK_UNPICKS]
    del self.checkpoints[Checkpoint.WALK_UNPICK]

  def _choose_final_squad(self, team: int, leader: int):
    # The leader of the second fireteam will not die under several conditions:
    # 1. They are loyal and ideal
    # 2. They are special-cased (Miranda)
    # 3. There are fewer than four active teammates (including the leader).
    alive = bool(leader & self.loyal & IDEAL_LEADERS.value)
    alive = alive or bool(leader & IMMORTAL_LEADERS.value)
    if not (alive or bits.popcount(team) < 4):
      team &= ~leader
    # Iterate through all possible final squads.
    ckpt_squad = self.checkpoints.get(Checkpoint.FINAL_SQUAD, 0)
    squads = combinations(bits.bits(team & ~bits.mtz(ckpt_squad)), 2)
    for squad_tuple in squads:
      squad: int = reduce(op_or, squad_tuple)
      if ckpt_squad and squad != ckpt_squad:
        continue
      ckpt_squad = 0
      self.set_checkpoint(Checkpoint.FINAL_SQUAD, squad)
      # The remaining active teammates form the defense team.
      victims = death.get_defense_victims(team & ~squad, self.loyal)
      # Any member of your squad that is not loyal will die.
      victims |= squad & ~self.loyal
      # Any active teammates at this point have survived.
      self.record_outcome(team & ~victims)
    del self.checkpoints[Checkpoint.FINAL_SQUAD]