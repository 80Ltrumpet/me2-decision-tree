#
# Copyright (c) 2022 Andrew Lehmer
#
# Distributed under the MIT License.
#

# Usage: python [-i] -m me2 <file>

import atexit
from itertools import combinations
import sys
from threading import Thread
from time import sleep, strftime

from .bits import bit_indices, ffs
from .dt import *

# Parse command-line arguments.
if len(sys.argv) < 2:
  print("Usage: python [-i] -m me2 <path to data file>", file=sys.stderr)
  sys.exit(2)

dt_file_path = sys.argv[1]
dt = DecisionTree(dt_file_path)
outcomes = dt.outcomes.items()


def counts():
  """Prints the number of traversals and outcomes recorded in the decision
  tree."""
  print(sum(n for _, (n, _) in outcomes), "traversals")
  print(len(outcomes), "outcomes")


def progress():
  """Prints a rough indication of progress in the decision tree generation."""
  if dt.is_complete():
    print("Complete (100%)")
    return
  while True:
    try:
      n_opt = dt.checkpoints[Checkpoint.N_OPT]
      recruits = tuple(bit_indices(dt.checkpoints[Checkpoint.RECRUITS]))
      choices = list(combinations(bit_indices(RECRUITABLE.value), n_opt))
      loyalty = dt.checkpoints[Checkpoint.LOYALTY] & LOYALTY_MASK.value
      break
    except KeyError:
      # All checkpoints are only set at a certain depth in the decision tree,
      # so waiting a bit before retrying the above query is usually sufficient.
      sleep(0.1)
  # Loyalties are only iterated for recruited allies.
  shift_to = ffs(OPTIONAL.value)
  ally_count = abs(n_opt) + shift_to
  opt_loyalty = 0
  for r in recruits:
    opt_loyalty |= (loyalty >> (r - shift_to)) & (1 << shift_to)
    shift_to += 1
  loyalty &= REQUIRED.value
  loyalty |= opt_loyalty
  index = choices.index(recruits)
  print(f"{n_opt - 2}/5 -> ", end="")
  print(f"{index + 1}/{len(choices)} -> ", end="")
  print(f"{loyalty + 1}/{1 << ally_count}")
  print(strftime("%H:%M:%S"))


# Main logic
if dt.is_complete():
  print("The decision tree is fully generated!")
  print("Use outcomes to view the decision tree outcome dictionary.")
else:
  if not outcomes:
    print(f"WARNING: '{dt.file_path}' is empty or does not exist.")
    print("This is expected on the first run.")

  if sys.flags.interactive:
    print("Generating the decision tree in a daemon thread.")
    thread = Thread(target=dt.generate)
    thread.daemon = True
    thread.start()
    # Allow quit() to exit cleanly.
    def pause_and_join():
      print("Pausing. Please wait...", flush=True)
      dt.pause()
      thread.join()
      counts()
    atexit.register(pause_and_join)
    # Interactive session intro
    print()
    print("Use outcomes to view the decision tree outcome dictionary.")
    print("Use counts() to print the current number of traversals and "
          "outcomes.")
    print("Use progress() to print the current iterations of the first three "
          "decisions.")
    print()
  else:
    print("Generating the decision tree...")
    dt.generate()
    if not dt.is_complete():
      print("Paused")

if not sys.flags.interactive:
  counts()