#! /usr/bin/env python3 -i

import atexit
from me2.dt import *
import sys
from threading import Thread

if len(sys.argv) < 2:
  print(f'Usage: python -i {sys.argv[0]} <path to data file>')
  sys.exit(2)
dt_file_path = sys.argv[1]

dt = DecisionTree(dt_file_path)
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
    print('Successfully paused decision tree generation.')

outcomes = dt.outcomes.items()
def counts() -> None:
  print(sum(i[1][0] for i in outcomes), 'traversals')
  print(len(outcomes), 'outcomes')

print()
print('Use outcomes to view the decision tree outcome dictionary.')
print('Use counts() to print the current number of traversals and outcomes.')
print()