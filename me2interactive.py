#! /usr/bin/env python3 -i

import atexit
from me2.dt import *
import sys
from threading import Thread
from time import sleep

if len(sys.argv) < 2:
  print(f'Usage: python -i {sys.argv[0]} <path to data file>')
  sys.exit(2)
dt_file_path = sys.argv[1]

dt = DecisionTree(dt_file_path)
outcomes = dt.outcomes.items()

# Some useful functions
def counts() -> None:
  print(sum(i[1][0] for i in outcomes), 'traversals')
  print(len(outcomes), 'outcomes')

def progress() -> None:
  try:
    n_opt = dt.memo[MemoKey.N_OPT.name]
    if not n_opt:
      print('Complete')
      return
    recruits = tuple(bit_indices(dt.memo[MemoKey.RECRUITS.name]))
    choices = list(combos(bit_indices(RECRUITABLE.value), n_opt))
    loyalty = dt.memo[MemoKey.LOYALTY.name] & LOYALTY_MASK.value
    print(f'{n_opt - 2}/5 -> ', end='')
    print(f'{choices.index(recruits) + 1}/{len(choices)} -> ', end='')
    print(f'{loyalty + 1}/{Ally.Morinth.value}')
  except KeyError:
    sleep(0.1)
    progress()

# Start decision tree generation, if needed.
if dt.is_complete():
  print('The decision tree is fully generated!')
else:
  if not dt.outcomes:
    print(f"WARNING: '{dt_file_path}' is empty or does not exist.")
  print('Generating decision tree in a daemon thread.')
  dt_thread = Thread(target=dt.generate)
  dt_thread.daemon = True
  dt_thread.start()
  @atexit.register
  def dt_pause_and_join() -> None:
    print('Pausing. Please wait...', flush=True)
    dt.pause()
    dt_thread.join()
    counts()

# Console intro
print()
print('Use outcomes to view the decision tree outcome dictionary.')
print('Use counts() to print the current number of traversals and outcomes.')
print('Use progress() to print the current iterations of the first three decisions.')
print()