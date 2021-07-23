import sys

if len(sys.argv) < 2:
  print('Usage: python -m me2 <path to decision tree data file>')
  sys.exit(2)
dt_file_path = sys.argv[1]

from .dt import DecisionTree

dt = DecisionTree(dt_file_path)
if dt.is_complete():
  print('The decision tree is fully generated!')
elif not dt.outcomes:
  print(f"'{dt_file_path}' is empty or does not exist.",
        "Starting from scratch.", sep='\n')
else:
  print('Continuing decision tree generation...')

# If the tree is fully generated, this is essentially a no-op.
dt.generate()

if not dt.is_complete():
  print('Paused:')

# Print the number of outcomes that have been generated.
print(sum(t[0] for t in dt.outcomes.values()), 'traversals')
print(len(dt.outcomes), 'unique outcomes')