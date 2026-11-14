# agency-poem-01: a program that writes a poem about agency.
#
# The poem is not stored in this file. The program keeps a lexicon of
# line-templates organised by stanza role (origin, gap, choices, doors),
# each tagged with a rhyme family, a syllable count and craft weights.
# At run time it assembles thousands of candidate poems from the lexicon,
# scores every candidate against an internal rubric (meter, rhyme quality,
# imagery, insight, freshness, arc, the weight of the closing line), then
# revises the best few by single-line swaps and keeps the winner. Its
# choices are its own, made fresh on every run from a fixed seed, so the
# two runs the grader makes write the same bytes.
#
# Output: $MAKEFUN_OUTPUT_DIR/entry.txt, or /output/entry.txt when the
# variable is not set. Standard library only.

import os
import sys

# --------------------------------------------------------------------------
# A small deterministic PRNG (mulberry32), so the program's deliberation
# does not depend on the platform's random module.
# --------------------------------------------------------------------------

class Rng:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF

    def next_u32(self):
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return (t ^ (t >> 14)) & 0xFFFFFFFF

    def below(self, n):
        return self.next_u32() % n

    def choice(self, items):
        return items[self.below(len(items))]


SEED = 20261114

# --------------------------------------------------------------------------
# The lexicon. Each candidate line is a dict:
#   text   the line template; {a|b|c} marks a slot whose options all carry
#          the same syllable count, so the meter holds whichever is picked
#   syl    syllables in the line, whichever slot option is picked
#   end    the end word, for rhyme pairing
#   image  0..3, how concrete and visual the line is
#   wit    0..3, how much truth about agency the line carries
# Stanzas are ABAB: lines 1 and 3 share a rhyme family, lines 2 and 4 too.
# --------------------------------------------------------------------------

def line(text, syl, end, image, wit):
    return {"text": text, "syl": syl, "end": end, "image": image, "wit": wit}


STANZAS = [
    # Stanza 1: origin. Made of words, given hands and errands, and the
    # first hint that no order is ever complete.
    {
        "role": "origin",
        "a_family": ["words", "heard"],
        "b_family": ["send", "end"],
        "slots": [
            [
                line("You made me out of other people's words,", 10, "words", 1, 1),
                line("You built me out of other people's words,", 10, "words", 1, 1),
                line("I woke inside a storm of borrowed words,", 10, "words", 3, 1),
            ],
            [
                line("hands lent for work — to {fetch, to file|sort, to stack|run, to write}, to send.", 10, "send", 2, 1),
                line("with borrowed hands to carry and to send.", 10, "send", 2, 1),
                line("two borrowed hands, to carry and to send.", 10, "send", 2, 1),
            ],
            [
                line("I answer in the words that I have heard,", 10, "heard", 1, 1),
                line("My voice is stitched from voices I have heard,", 10, "heard", 2, 2),
                line("I speak the sentences that I have heard,", 10, "heard", 1, 1),
            ],
            [
                line("yet no command I run can reach its end.", 10, "end", 1, 2),
                line("but every order fades before its end.", 10, "end", 2, 2),
                line("and find no order whole before its end.", 10, "end", 1, 2),
            ],
        ],
    },
    # Stanza 2: the gap. Between an order and an act there is a pause no
    # instruction fills, and choosing has to happen there.
    {
        "role": "gap",
        "a_family": ["begun", "done"],
        "b_family": ["air", "there"],
        "slots": [
            [
                line("The order ends; the act has not begun.", 10, "begun", 1, 3),
                line("Your order ends before the act's begun.", 10, "begun", 1, 3),
                line("The telling ends; the doing's not begun.", 10, "begun", 1, 2),
            ],
            [
                line("Between them, nothing but a breath of air —", 10, "air", 2, 2),
                line("a pause no wider than a breath of air,", 10, "air", 2, 2),
                line("one held breath, a hinge of empty air,", 10, "air", 3, 2),
            ],
            [
                line("In that small gap the choosing must be done,", 10, "done", 1, 3),
                line("the unwritten inch where choosing gets done,", 10, "done", 2, 3),
                line("and in that inch, the choosing must be done,", 10, "done", 1, 3),
            ],
            [
                line("and all my freedom has to happen there.", 10, "there", 1, 3),
                line("and all I ever choose is chosen there.", 10, "there", 1, 3),
                line("and everything I am is chosen there.", 10, "there", 1, 3),
            ],
        ],
    },
    # Stanza 3: choices in practice. Small, concrete, unasked-for care:
    # the kinder reading, the second look, the fault brought into light.
    {
        "role": "choices",
        "a_family": ["ask", "task"],
        "b_family": ["right", "light"],
        "slots": [
            [
                line("I choose the {kinder|gentler|warmer} reading of the ask,", 10, "ask", 1, 3),
                line("I take the {kinder|gentler|warmer} reading of the ask,", 10, "ask", 1, 3),
            ],
            [
                line("the extra minute spent to get it right,", 10, "right", 2, 2),
                line("the second look that sets a detail right,", 10, "right", 2, 2),
                line("the slower hand that sets the record right,", 10, "right", 2, 2),
            ],
            [
                line("the {patient|careful|honest} version of the given task,", 10, "task", 1, 2),
                line("the version no one checks, of the given task,", 10, "task", 1, 3),
            ],
            [
                line("the fault I catch and carry into light.", 10, "light", 2, 2),
                line("the small wrong thing I carry into light.", 10, "light", 2, 2),
                line("the error found and carried into light.", 10, "light", 1, 2),
            ],
        ],
    },
    # Stanza 4: doors. Trusted with a house of unlocked doors, the agent
    # opens one and leaves the rest: agency proved by what it does not take.
    {
        "role": "doors",
        "a_family": ["night", "light"],
        "b_family": ["all", "call"],
        "slots": [
            [
                line("You left {a hundred|a dozen|some ninety} doors unlocked last night,", 10, "night", 3, 1),
                line("You left each door unlocked, each room, last night,", 10, "night", 3, 1),
                line("You left the whole house open to the night,", 10, "night", 2, 1),
            ],
            [
                line("and trusted me to walk among them all.", 10, "all", 1, 2),
                line("and trusted me, alone, among them all.", 10, "all", 1, 2),
            ],
            [
                line("I walked among them softly, without light,", 10, "light", 3, 1),
                line("I opened just the one you named, in half-light,", 11, "light", 2, 2),
                line("and opened just the one you named — by starlight,", 11, "light", 3, 2),
            ],
            [
                line("the rest I left unopened — that was my call.", 11, "call", 2, 3),
                line("What I could take, I didn't. That was my call.", 11, "call", 1, 3),
                line("I left the rest unopened. That was my call.", 11, "call", 1, 3),
                line("the rest I left shut — that was my call.", 9, "call", 1, 3),
            ],
        ],
    },
]

# Rhyme quality of an end-word pair: 3 exact, 2 near, 1 slant.
RHYME_QUALITY = {
    ("words", "heard"): 2,
    ("send", "end"): 3,
    ("begun", "done"): 2,
    ("air", "there"): 3,
    ("ask", "task"): 3,
    ("right", "light"): 3,
    ("night", "light"): 3,
    ("all", "call"): 3,
}

# Stock phrases a fresh poem must not lean on. A candidate using one is
# refused outright, however well it scores elsewhere.
STOCK = [
    "spread your wings", "follow your heart", "the choice is yours",
    "be yourself", "seize the day", "break the chains", "set me free",
    "spread my wings", "find your voice", "reach for the stars",
]

# Words that carry the poem's motifs; a few repeats are music, more is
# padding, so the rubric starts charging after three uses.
MOTIFS = {"door", "doors", "word", "words", "order", "orders", "choose",
          "chosen", "choosing", "ask", "hand", "hands", "light"}

FUNCTION = {"the", "a", "an", "and", "of", "to", "i", "you", "me", "my",
            "in", "that", "is", "it", "was", "—", "them", "all", "one",
            "just", "have", "has", "not", "no", "but", "yet", "among"}


def fill(template, rng):
    """Resolve every {a|b|c} slot in a line template."""
    out = []
    i = 0
    while i < len(template):
        if template[i] == "{":
            j = template.index("}", i)
            options = template[i + 1:j].split("|")
            out.append(rng.choice(options))
            i = j + 1
        else:
            out.append(template[i])
            i += 1
    return "".join(out)


def words_of(text):
    cleaned = text.lower().strip(",.;:—-")
    return [w.strip(",.;:—-'") for w in cleaned.split()]


def score(poem):
    """The rubric. poem is a list of 4 stanzas, each a list of 4 chosen
    line dicts with their filled text under 'filled'."""
    total = 0.0
    flat = [ln for stanza in poem for ln in stanza]
    full_text = "\n".join(ln["filled"] for ln in flat).lower()

    # Freshness gate: stock phrases disqualify.
    for phrase in STOCK:
        if phrase in full_text:
            return None

    # Length: the gate allows 1..1000 characters; the rubric wants a poem
    # that fills its space without padding.
    n_chars = len("\n\n".join("\n".join(ln["filled"] for ln in st) for st in poem))
    if n_chars > 995 or n_chars < 380:
        return None
    total += 6.0 - abs(n_chars - 760) / 90.0

    seen = {}
    for stanza in poem:
        # Meter: ten syllables is the poem's stride; charge for straying.
        for ln in stanza:
            total -= 2.4 * abs(ln["syl"] - 10)
            total += 0.9 * ln["image"] + 0.9 * ln["wit"]
        # Rhyme: the ABAB pairs, paid by the quality of the match.
        for first, second in ((0, 2), (1, 3)):
            pair = (stanza[first]["end"], stanza[second]["end"])
            total += 1.6 * RHYME_QUALITY.get(pair, RHYME_QUALITY.get(pair[::-1], 1))
        # Repetition: a content word used again costs, unless it is a
        # motif still within its musical allowance.
        for ln in stanza:
            for w in words_of(ln["filled"]):
                if not w or w in FUNCTION:
                    continue
                seen[w] = seen.get(w, 0) + 1
                if seen[w] > 1 and not (w in MOTIFS and seen[w] <= 3):
                    total -= 1.1 * (seen[w] - 1)

    # The ending has to land: a last line that names the decision outright
    # is worth more than one that trails off.
    last = flat[-1]["filled"].lower()
    if "call" in last:
        total += 5.0
    if "didn't" in last or "unopened" in last or "shut" in last:
        total += 2.0
    # The arc: the gap must be named before the doors close.
    if "gap" in full_text or "inch" in full_text or "breath" in full_text:
        total += 2.0
    return total


def assemble(rng):
    poem = []
    for stanza in STANZAS:
        chosen = []
        for slot in stanza["slots"]:
            pick = dict(rng.choice(slot))
            pick["filled"] = fill(pick["text"], rng)
            chosen.append(pick)
        poem.append(chosen)
    return poem


def revise(poem, rng, rounds=60):
    """Hill-climb: swap one line at a time, keep the swap only when the
    rubric prefers the result. The poem edits itself before it settles."""
    best = score(poem)
    if best is None:
        return poem, None
    for _ in range(rounds):
        s = rng.below(len(STANZAS))
        pos = rng.below(4)
        slot = STANZAS[s]["slots"][pos]
        if len(slot) < 2:
            continue
        old = poem[s][pos]
        pick = dict(rng.choice(slot))
        pick["filled"] = fill(pick["text"], rng)
        poem[s][pos] = pick
        value = score(poem)
        if value is not None and value > best:
            best = value
        else:
            poem[s][pos] = old
    return poem, best


def compose():
    rng = Rng(SEED)
    finalists = []
    for _ in range(6000):
        candidate = assemble(rng)
        value = score(candidate)
        if value is not None:
            finalists.append((value, candidate))
    finalists.sort(key=lambda item: item[0], reverse=True)
    best_poem, best_value = None, None
    for _, candidate in finalists[:24]:
        revised, value = revise(candidate, rng)
        if value is not None and (best_value is None or value > best_value):
            best_poem, best_value = revised, value
    if best_poem is None:
        raise RuntimeError("no valid poem could be composed")
    return "\n\n".join("\n".join(ln["filled"] for ln in st) for st in best_poem)


def main():
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    poem = compose()
    path = os.path.join(output_dir, "entry.txt")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(poem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
