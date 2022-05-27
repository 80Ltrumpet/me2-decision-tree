# Outcome Enumerator for _Mass Effect 2_

> This document assumes the reader is familiar with the entirety of _Mass
> Effect 2_, including references and terminology that may be considered
> spoilers. You have been warned! :)

This Python package models a decision tree for all player actions affecting
the survival of allied characters at the end of _Mass Effect 2_ and, to a
certain extent, _Mass Effect 3_ (see [Limitations](#limitations)). The output
of the decision tree is a mapping between unique _outcomes_ and ordered pairs
containing the following data:

1.  The number of unique _traversals_ that lead to the outcome
1.  An example of one such traversal encoded as an integer

An _outcome_ encodes the following information into a single integer:

- Which allies survived?
- Which surviving allies were _loyal_?
  - An ally becomes loyal if the player successfully completes their _loyalty
    mission_.
- Was the surviving crew of the Normandy SR2 rescued?
  - For the purposes of discussion, "the surviving crew" refers to the group
    that is still alive when Shepard arrives to rescue them.

A _traversal_ encodes a path through the decision tree, which is discussed
further in [its own section](#decision-tree). The output can be used to find
answers to some interesting questions, such as

- How likely is it for a particular ally to survive the final mission?
- How likely is it for Shepard to die?
- How many outcomes can only be achieved by making a unique set of decisions?
- How many different outcomes can be achieved?
- What is the most likely outcome?

See [Interesting Facts](#interesting-facts) for some answers to these and other
questions.

Some player actions and their consequences are not considered in the scope of
this project. See [Limitations](#limitations) for a discussion of the rationale
behind the exclusions.

## Interesting Facts

- The decision tree covers 39,600,351,708 traversals!
- There are 697,887 _achievable_ outcomes of 1,417,176 _potential_ outcomes.
  - That means there are 719,289 outcomes that are impossible to achieve.
- 111 outcomes are uniquely achievable (i.e., they have only one traversal).
  - These outcomes have the following in common:
    - Miranda survives and is loyal.
    - Garrus is _not_ loyal.
    - Jacob is _not_ loyal.
  - Note that Garrus, Jacob, and Miranda are all _ideal leaders_. That is, if
    they are loyal when selected as a leader during the final mission, a death
    will be avoided.
- The greatest number of traversals for any outcome is 62,147,162.
  - Unsurprisingly, that outcome spares only loyal Jacob, loyal Miranda, and
    the crew.
- The ten most common outcomes cover 373,227,856 traversals.
- The one hundred most common outcomes cover 1,767,031,966 traversals.
- The one thousand most common outcomes cover 6,807,718,024 traversals.
- Morinth is more likely to survive than a loyal Samara.
  - Loyal Samara's survival rate is 87.1% of Morinth's.
- There are 324,677,659 ways to prevent Shepard from surviving the final
  mission. This can only happen if less than two allies survive.
  - In other words, **Shepard survives 99.18%** of all traversals.

### Ally Survival Rates

| Name    | Relative | Absolute |
| ------- | -------- | -------- |
| Miranda | 1.000    | 0.705    |
| Jacob   | 0.840    | 0.592    |
| Zaeed   | 0.780    | 0.549    |
| Garrus  | 0.647    | 0.456    |
| Grunt   | 0.623    | 0.439    |
| Mordin  | 0.508    | 0.358    |
| Samara  | 0.489    | 0.345    |
| Kasumi  | 0.443    | 0.312    |
| Legion  | 0.433    | 0.305    |
| Tali    | 0.425    | 0.299    |
| Thane   | 0.422    | 0.297    |
| Jack    | 0.389    | 0.274    |

> NOTE: Morinth is not included in the table above due to her dependence on
> Samara's loyalty mission.

> NOTE: Survival implies recruitment. That is, if an ally is not recruited,
> they are **not** regarded as surviving.

## Decision Tree

The decision tree is not strictly modeled as a _tree_ in the mathematical
sense. It is akin to a directed, acyclical graph (DAG) with a root node, and
traversing the graph accumulates state. That state is the traversal encoding
which maps onto a unique root-to-leaf traversal of the analogous tree.

Some decisions affect the availability of future choices. The decisions that
are considered are described below in "plain English." The bare logic can be
found in the `DecisionTree` class in the [`dt` module](me2/dt.py).

1.  How many optional allies will be recruited?
    - Garrus, Jack, Jacob, Miranda, and Mordin (five) are required. All others
      are optional, but eight is the minimum number of allies necessary to
      complete the game, so at least three must be chosen.
1.  Which optional allies will be recruited?
    - Do not consider Morinth in this decision (see #4).
1.  Which allies' loyalty missions will be completed?
1.  Will Morinth replace Samara?
    - This decision is only considered if Samara is recruited and loyal.
1.  Will the Silaris Armor upgrade be purchased?
    - If not, Jack dies.
1.  Will the Cyclonic Shields upgrade be purchased?
    - If not, an ally will die according to a certain priority.
1.  Which allies will join the squad that defends the cargo bay?
    - This decision is only considered if the shields were not upgraded because
      the allies in your squad will _not_ die even if they would have been
      prioritized for death.
1.  Will the Thanix Cannon upgrade be purchased?
    - If not, an ally will die according to a certain priority.
1.  Which ally will act as the first tech specialist?
    - If they are not loyal and one of Kasumi, Legion, or Tali, they will die.
1.  Which ally will lead the first fireteam?
    - This decision is only considered if the first tech specialist would
      survive according to the previous decision.
    - If the first fireteam leader is not loyal and one of Garrus, Jacob, or
      Miranda, the first tech specialist will die.
1.  Which ally will act as the biotic specialist?
1.  Which ally will lead the second fireteam?
    - If they are (1) not Miranda, (2) not loyal or one of Garrus or Jacob,
      they _may_ die. They will _not_ die if there are fewer than four allies
      remaining to choose for your squad for the final battle (see #16).
1.  Will an ally escort the crew?
    - If there are four or fewer total allies remaining, no one is allowed to
      escort the crew.
1.  Which ally will escort the crew?
    - This decision is only considered according to the previous choice.
    - If they are not loyal, they will die. Otherwise, they are guaranteed to
      survive the final mission.
1.  Which allies will join your squad under the protection of the biotic
    specialist?
    - This decision is only considered if the biotic specialist is not loyal
      and one of Jack, Samara, or Morinth because an ally in your squad will
      die according to a certain priority.
1.  Which allies will join your squad for the final battle?
    - Any disloyal ally in your squad will die after the final battle.
    - All remaining allies (except the crew escort, if applicable) are left
      behind to _hold the line_. Their survival is dependent on a formula
      that is too complex to describe here. See the [References](#references)
      for a flowchart, or check out `get_defense_victims()` in the
      [`death` module](me2/death.py).

All of the choices made for each decision above are decodable from an encoded
traversal, which is stored as a single integer.

> Decision #15 was the most technically challenging to implement due to the
> fact that _not_ picking an ally for your squad can spare them from the
> consequence of choosing a bad biotic specialist.

## Usage

Most of the code in the `me2` package can be treated like documentation. The
interesting part is probing the data that has already been generated and
included in this repository. The easiest way to get started is with an
interactive Python session.

```python
$ python -im me2 me2.dat
The decision tree is fully generated!
Use outcomes to view the decision tree outcome dictionary.
>>> len(outcomes)
697887
>>> print(next(iter(outcomes)))
(160, (341198, 562069081815085676543))
```

`outcomes` is a view of dictionary items, and all data is encoded as `int`s.
You can get human-readable output like so:

```python
>>> item = next(iter(outcomes))
>>> print(describe_outcome(item[0]))
Survived: (2) Grunt and Legion
Loyal:    nobody
Crew:     dead
>>> print(describe_traversal(item[1][1]))
No Normandy upgrades.
Recruit: Grunt, Kasumi, Legion, Morinth, Samara, Tali, Thane, and Zaeed
Loyalty Missions: Garrus, Jack, Jacob, Samara, Tali, and Thane
For the cargo bay squad, pick Kasumi and Legion.
Choose Jacob as the tech specialist.
The second fireteam leader does not matter.
Choose Miranda as the biotic specialist.
Choose Morinth to lead the diversion team.
Do not send anyone to escort the crew.
For the squad in the biotic shield, pick Garrus.
Pick Miranda and Zaeed for your final squad.
```

You can also request a brief description of an outcome.

```python
>>> print(describe_outcome(item[0], brief=True))
2 allies survived.
```

More intelligent queries currently require knowledge of the outcome encoding.
For example, this is how one would ask, "What percentage of traversals result
in Jacob's death?"

```python
>>> jacob_dies = sum(e[1][0] for e in outcomes if ~e[0] & Ally.Jacob.value)
>>> total = sum(e[1][0] for e in outcomes)
>>> jacob_dies / total
0.40816029779691876
```

So, roughly 41%, as it turns out. This is not user-friendly, but at least it
is not impossible to do.

### Generating Data

> Full disclosure: On my machine, it took several _days_ to generate the data
> file. If you are curious enough to try anyway, read on.

To run the decision tree, point the `me2` package at a non-existent or
incomplete file.

```bash
$ python -m me2 path/to/file
# or interactively
$ python -im me2 path/to/file
```

In non-interactive mode, the decision tree will run until an interrupt signal
(Ctrl-C) is issued. In interactive mode, you can manually request progress
information with `progress()` or a running total of traversals with `counts()`.
Use `quit()` like usual when you want to stop.

In either case, ending the program will pause the output generation. All
information required for the script to pick up where it left off is saved in
the file along with the actual outcome and traversal data. The file is
considered _incomplete_, but restarting with the same file will automatically
continue generating data.

## Limitations

The following subsections discuss some of the known and perceived limitations
of the design.

### Partial Data

Each outcome was achieved via one or more traversals of the decision tree, but
only the traversal count and _one_ encoded traversal is included with each
outcome in the output data. Why?

It comes down to speed and storage constraints. Some quick math shows that even
with an ideal serialization scheme, the size of the output data would quickly
become unreasonable.

1.  There are ~39.6 **billion** traversals.
1.  The shortest traversal encoding is 48 bits (6 bytes) long.
    - They are at most 70 bits (8.75 bytes) long.
1.  In the _best_ case, 39.6 billion times 6 bytes is about **220 GiB**.

By today's standards, that is still considered a gigantic amount of storage,
especially for such a trivial use case. Forget about trying to load and query
a file of that size, too.

In the end, the outcomes are the most interesting data to analyze, and the most
interesting traversals are the ones that led to rare outcomes. By including one
traversal for each outcome, we get the best of both worlds.

### Scope

The scope of this project is limited to only the parameters that affect the
fate of _Mass Effect 2_ allies when carried over to _Mass Effect 3_. If an
ally survives _ME2_, they will be encounterable in _ME3_. Furthermore, if the
ally was loyal, they may become a war asset in _ME3_. If they were not loyal,
however, they would die in _ME3_.

However, there is one member of the crew of the Normandy SR2 who is not
specifically addressed in this implementation: YN Kelly Chambers. Outcomes
only encode _whether_ the crew was rescued, but that is only part of the story.
Some of the crew may die _before_ they are rescued based on the number of
missions completed after the installation of the Reaper IFF.

| Missions | Result                                              |
| -------- | --------------------------------------------------- |
| 0        | Everyone in the crew survives.                      |
| 1–3      | Half of the crew dies, including YN Kelly Chambers. |
| >3       | Everyone except Dr. Karen Chakwas dies.             |

Both Chambers and Chakwas return in _ME3_ if they survive the final mission of
_ME2_, and Chambers even has an "implicit loyalty" in _ME2_ that factors into
her fate in _ME3_. So, why are they not explicitly considered in the decision
tree? In Dr. Chakwas's case, her survival is entirely dependent on whether an
escort is selected, so one could argue that the crew survival encoding in the
outcome should be called the "Dr. Chakwas survival bit." For YN Chambers, this
is just an unfortunate gap. To address this, I would make the following changes:

- Add a _Kelly Chambers loyalty_ decision (true/false).
- Add a _post-Reaper-IFF mission completion_ decision (0/1–3/>3).
- Reinterpret the existing crew survival outcome bit as the _Dr. Chakwas
  survival_ bit.
- Add a _Kelly Chambers survival_ bit to the outcome encoding.
- Add a _Kelly Chambers loyalty_ bit to the outcome encoding.

### Usability

It is painful to query encoded outcome data. This project is missing a
well-designed `query` module/API.

## References

This project was made possible by the amazing folks in the _Mass Effect_
community, particularly those who took the time to answer some esoteric
questions on the
[_Mass Effect_ subreddit](https://www.reddit.com/r/masseffect/). Of particular
importance was
[this flowchart](https://external-preview.redd.it/7SeMlQbU-xFC9TjKurncqx1y8NH3RJiolYRqFAoXfWg.jpg?auto=webp&s=a57ad480a357234ec7fa5f865b00b60b95670df0)
for which I regrettably am unable to find any attribution, though I believe
that particular version was distilled from a primary source unknown to me.
