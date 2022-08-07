# Encodings

## Outcome

### Original

| Bits    | Description   |
| ------- | ------------- |
| `12: 0` | Spared allies |
| `24:13` | Loyal allies  |
| `25:25` | Crew survival |

> If Morinth is spared, she is loyal, so there is no loyalty bit allocated for
> her.

> The "crew survival" bit only guarantees Dr. Chakwas' survival, as the
> original traversal encoding does not encode decisions that determine the
> survival of other members of the crew.

### Proposed

| Bits    | Description   |
| ------- | ------------- |
| `12: 0` | Spared allies |
| `24:13` | Loyal allies  |
| `26:25` | Crew survival |

> Bits `24:0` are exactly the same as the original encoding.

Crew survival now encompasses four possible outcomes.

| Value | Description                                                        |
| ----: | ------------------------------------------------------------------ |
|     0 | No one survives.                                                   |
|     1 | Only Dr. Chakwas survives.                                         |
|     2 | Dr. Chakwas and half of the crew survive, but Kelly Chambers dies. |
|     3 | Everyone survives.                                                 |

> This proposal is _backward incompatible_ with the original encoding.

## Traversal

### Original

The original traversal encoding used a variable, conditional format, so many
bit positions for certain decisions were not guaranteed, making decoding and
comparisons a nightmare. As such, bit counts are given in the table below
instead of absolute bit positions.

| Bits | Description                              | Condition           |
| ---: | ---------------------------------------- | ------------------- |
|    8 | Optional ally recruitment                |                     |
|   12 | Loyalty missions                         |                     |
|    1 | Purchased the armor upgrade              |                     |
|    1 | Purchased the shield upgrade             |                     |
|    1 | Purchased the weapon upgrade             |                     |
|    9 | Cargo bay squad selection                | No shield upgrade   |
|    4 | Tech specialist                          |                     |
|    1 | First fireteam leader is loyal and ideal | Loyal/ideal tech    |
|    3 | Available, loyal, ideal leaders          | Loyal/ideal tech    |
|    4 | Biotic specialist                        |                     |
|    4 | Second fireteam leader                   |                     |
|    4 | Crew escort (can be nobody)              |                     |
|    1 | _The Long Walk_ squad selection matters  |                     |
|    9 | Inverted _The Long Walk_ squad selection | Previous bit is set |
|    8 | Final squad selection                    |                     |

> If Morinth is recruited, she must be loyal, so there is no loyalty mission
> bit allocated for her.

> Based on conditionally included bit fields, the minimum encoding length is
> 48 bits, and the maximum encoding length is 70 bits.

### Proposed

The following table describes a static, word-aligned encoding.

| Word | MSB | LSB | Description                                 | Footnote |
| ---: | --: | --: | ------------------------------------------- | -------- |
|    0 |  11 |   0 | Loyalty missions                            |          |
|      |  12 |  12 | Purchased the armor upgrade                 |          |
|      |  13 |  13 | Purchased the shield upgrade                |          |
|      |  14 |  14 | Purchased the weapon upgrade                |          |
|      |  15 |  15 | Crew rescue possible                        | 1        |
|      |     |     |                                             |          |
|    1 |   7 |   0 | Optional ally recruitment                   |          |
|      |  15 |   8 | Final squad selection                       |          |
|      |     |     |                                             |          |
|    2 |   3 |   0 | Tech specialist                             |          |
|      |   7 |   4 | Biotic specialist                           |          |
|      |  11 |   8 | Second fireteam leader                      |          |
|      |  15 |  12 | Crew escort                                 |          |
|      |     |     |                                             |          |
|    3 |   8 |   0 | Cargo bay squad selection                   |          |
|      |   9 |   9 |                                             |          |
|      |  11 |  10 | Optional post-Reaper-IFF mission completion | 2        |
|      |  15 |  12 | First fireteam leader selection             | 3        |
|      |     |     |                                             |          |
|    4 |   0 |   0 | _The Long Walk_ squad selection matters     |          |
|      |   9 |   1 | Inverted _The Long Walk_ squad selection    |          |
|      |  15 |  10 |                                             |          |

All fields use the same encodings as the original (unless
[footnoted](#footnotes)), but they are shuffled to ensure no quantity is broken
across a word boundary.

#### Footnotes

1.  This field indicates if it is possible to rescue the crew. If there are not
    enough available allies to spare an escort, this bit is cleared.

2.  This field indicates the completion of optional missions after completing
    the _Reaper IFF_ mission.

    | Value | Description                              |
    | ----: | ---------------------------------------- |
    |     0 | Zero optional missions                   |
    |     1 | One, two, or three optional missions     |
    |     2 | Four or more optional missions           |
    |     3 | Any number of missions (does not matter) |

    This field can be ignored if there is no crew escort.

3.  The two fields related to the first fireteam leader are merged to
    illustrate its interpretation as a single concept.

## Traversal Comparison

A static encoding for traversals enables a new feature: traversal comparison.
Bitfields from two traversals can be compared with applications of bit-wise
operations. Fields with value semantics (i.e., 4-bit ally indices) can be
compared with analogous logical operations.

Aggregate traversal information can be enriched with such comparisons. In
addition to storing one example of a traversal that achieves the associated
outcome, the following can be computed and stored for all of an outcome's
traversals:

1.  Which bits are always set?
1.  Which bits are always cleared?
1.  Are any allies always selected for a particular role?

There are 26 bits that are relevant for (1) and (2), and either 16 or 24 bits
for (3), depending on if the final squad selection is included.

> The final squad selection is a less straightforward comparison to compute,
> since the order of the selection does not matter. For example, if it turns
> out that Miranda is always selected for the final squad, she may be encoded
> in either the first or second "slot" in the traversal. That is, the aggregate
> comparison would have to check both slots. One way around this is to convert
> the squad selection to a bitfield, which only consumes five additional bits.

The estimated additional storage requirement per outcome based on the above is
between six and eight bytes, inclusive.
