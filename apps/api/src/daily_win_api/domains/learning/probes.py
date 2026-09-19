from daily_win_api.domains.learning.enums import ProbeType
from daily_win_api.domains.learning.support import INDEPENDENT, PARENT_ALLOWED_SUPPORT
from daily_win_api.domains.learning.taxonomy import is_academic_code

PROBE_CATALOG_VERSION = "assessment_probe_v2"
GENERIC_PROBE_TASK = "Invite one independent try at the planned skill."


def probe_for_skill(skill_code: str) -> dict[str, object]:
    catalog = _PROBES.get(skill_code)
    if catalog is None:
        return {
            "target_skill_code": skill_code,
            "probe_type": ProbeType.OBSERVE_INDEPENDENT_TRY.value,
            "observable_task": GENERIC_PROBE_TASK,
            "expected_outcome": "The child attempts the planned skill.",
            "success_criteria": "Independent correct attempt without a prompt.",
            "allowed_support": PARENT_ALLOWED_SUPPORT,
            "independent_means": INDEPENDENT,
            "false_positive": "Any try, including off-construct work.",
            "catalog_version": PROBE_CATALOG_VERSION,
        }
    return {**catalog, "catalog_version": PROBE_CATALOG_VERSION}


def has_construct_specific_probe(skill_code: str) -> bool:
    probe = _PROBES.get(skill_code)
    if probe is None:
        return False
    return str(probe.get("observable_task") or "") != GENERIC_PROBE_TASK


def academic_probe_codes() -> tuple[str, ...]:
    return tuple(sorted(_PROBES))


def _probe(
    code: str,
    probe_type: ProbeType,
    *,
    task: str,
    outcome: str,
    success: str,
    false_positive: str,
    counts: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "target_skill_code": code,
        "probe_type": probe_type.value,
        "observable_task": task,
        "expected_outcome": outcome,
        "success_criteria": success,
        "allowed_support": PARENT_ALLOWED_SUPPORT,
        "independent_means": INDEPENDENT,
        "false_positive": false_positive,
    }
    if counts:
        payload["attempt_structure"] = counts
    return payload


_PROBES: dict[str, dict[str, object]] = {
    "math.number_sense.counting": _probe(
        "math.number_sense.counting",
        ProbeType.COUNTED_ITEMS,
        task=(
            "Set out 8–10 objects. Ask the child to count them once, "
            "touching each object."
        ),
        outcome="Child counts the set without skipping or double-counting.",
        success="Independent accurate count of the whole set.",
        false_positive=(
            "Parent counting along, or the child reciting numbers without "
            "one-to-one pointing."
        ),
        counts="1 set of 8-10",
    ),
    "math.number_sense.compare": _probe(
        "math.number_sense.compare",
        ProbeType.COUNTED_ITEMS,
        task="Show two small groups (each 10 or fewer). Ask which group has more.",
        outcome="Child points to or names the larger group.",
        success="Independent correct comparison without being told the counts.",
        false_positive=(
            "Choosing the spread-out group by size/area rather than quantity."
        ),
        counts="2 groups",
    ),
    "math.addition.within_10": _probe(
        "math.addition.within_10",
        ProbeType.COUNTED_ITEMS,
        task="Ask one addition fact whose sum is 10 or less (objects allowed).",
        outcome="Child states the correct sum.",
        success="Correct independently on the first or second try.",
        false_positive=(
            "Parent naming the addends or the sum, or counting for the child."
        ),
        counts="1-2 items",
    ),
    "math.addition.within_20": _probe(
        "math.addition.within_20",
        ProbeType.COUNTED_ITEMS,
        task="Ask one addition fact whose sum is 11–20 (objects or fingers allowed).",
        outcome="Child states the correct sum.",
        success="Correct independently on the first or second try.",
        false_positive="A within-10 fact, or the parent totaling the objects.",
        counts="1-2 items",
    ),
    "math.addition.word_problems": _probe(
        "math.addition.word_problems",
        ProbeType.OBSERVE_INDEPENDENT_TRY,
        task=(
            "Tell one oral 'how many in all' story with a total of 10 or less. "
            "Do not say 'add' or give the equation."
        ),
        outcome="Child names the correct total for the story.",
        success="Independent correct total after hearing the story once.",
        false_positive=(
            "Solving a naked fact with no story, or the parent stating the operation."
        ),
    ),
    "math.subtraction.within_10": _probe(
        "math.subtraction.within_10",
        ProbeType.COUNTED_ITEMS,
        task=(
            "Ask one subtraction fact whose difference is 10 or less "
            "(objects allowed)."
        ),
        outcome="Child states the correct difference.",
        success="Correct independently on the first or second try.",
        false_positive=(
            "An addition fact, or the parent removing objects while naming "
            "the answer."
        ),
        counts="1-2 items",
    ),
    "math.subtraction.within_20": _probe(
        "math.subtraction.within_20",
        ProbeType.COUNTED_ITEMS,
        task="Ask one subtraction fact with a starting number 11–20 (objects allowed).",
        outcome="Child states the correct difference.",
        success="Correct independently on the first or second try.",
        false_positive=(
            "A within-10 subtraction, or the parent performing the take-away."
        ),
        counts="1-2 items",
    ),
    "math.multiplication.equal_groups": _probe(
        "math.multiplication.equal_groups",
        ProbeType.COUNTED_ITEMS,
        task=(
            "Show 2 or 3 equal groups of the same small number of objects "
            "(at most 5 in each group). Ask how many in all."
        ),
        outcome="Child names the total of the equal groups.",
        success="Independent correct total by skip-counting or adding the groups.",
        false_positive=(
            "Counting one group only, or reciting a times-table fact with no "
            "groups present."
        ),
        counts="2-3 equal groups",
    ),
    "math.fractions.halves_fourths": _probe(
        "math.fractions.halves_fourths",
        ProbeType.OBSERVE_INDEPENDENT_TRY,
        task=(
            "Show one simple whole (circle or sandwich drawing) already split into "
            "2 or 4 equal pieces. Ask the child to point to a half, then a fourth."
        ),
        outcome="Child points to a half and a fourth of the same whole.",
        success="Independent correct identification of both shares.",
        false_positive="Pointing to any piece, or choosing unequal parts as 'half'.",
    ),
    "reading.phonics.letter_sounds": _probe(
        "reading.phonics.letter_sounds",
        ProbeType.OBSERVE_INDEPENDENT_TRY,
        task=(
            "Show one letter (not in a word). Ask for the common sound, not "
            "the letter name."
        ),
        outcome="Child produces the common sound for that letter.",
        success="Independent correct sound without being told the name-as-sound.",
        false_positive="Saying the letter name (ay, bee) instead of the sound.",
    ),
    "reading.phonics.blend_cvc": _probe(
        "reading.phonics.blend_cvc",
        ProbeType.PRODUCE_SAMPLE,
        task=(
            "Show one CVC word (for example cat, sun, map). Ask the child to "
            "read it by blending."
        ),
        outcome="Child says the whole CVC word.",
        success="Independent blend without the parent saying the word first.",
        false_positive=(
            "Guessing from the picture, or repeating the word after the parent."
        ),
    ),
    "reading.fluency.smooth_oral": _probe(
        "reading.fluency.smooth_oral",
        ProbeType.PRODUCE_SAMPLE,
        task=(
            "Show one short familiar sentence of 6–8 words the child can decode "
            "(CVC-based). Ask them to read it aloud while looking at the print."
        ),
        outcome=(
            "Child reads the sentence looking at the words, with at most one "
            "sound-out pause."
        ),
        success="Independent oral reading of that sentence from print.",
        false_positive=(
            "Reciting a memorized line without looking, or the parent reading "
            "it first."
        ),
    ),
    "reading.vocabulary.context_clues": _probe(
        "reading.vocabulary.context_clues",
        ProbeType.RETELL,
        task=(
            "Say one sentence that clearly signals a new word "
            "(for example: 'The tiny pup was minute — so small it fit in a cup.'). "
            "Ask what the new word means in that sentence."
        ),
        outcome="Child gives a meaning that fits the sentence.",
        success="Independent meaning that matches the context, not a random guess.",
        false_positive="Repeating the word, or a definition the parent supplied.",
    ),
    "reading.comprehension.recall_details": _probe(
        "reading.comprehension.recall_details",
        ProbeType.RETELL,
        task=(
            "After a short read-aloud (a few sentences), ask one question "
            "about a specific detail."
        ),
        outcome="Child names a detail that was in the text.",
        success="Independent correct recall of that detail.",
        false_positive=(
            "A guess unrelated to the text, or the parent pointing to the sentence."
        ),
    ),
    "reading.comprehension.main_idea": _probe(
        "reading.comprehension.main_idea",
        ProbeType.RETELL,
        task=(
            "After reading a short passage, ask what the passage was mostly about. "
            "Do not offer title choices that give the answer."
        ),
        outcome="Child states the central idea rather than one isolated detail.",
        success="Independent main-idea statement in their own words.",
        false_positive=(
            "Retelling one tiny side detail, or repeating the last sentence only."
        ),
    ),
    "reading.comprehension.simple_inference": _probe(
        "reading.comprehension.simple_inference",
        ProbeType.RETELL,
        task=(
            "Read one or two sentences that imply something unstated "
            "(for example: 'Maya grabbed her umbrella and boots.'). "
            "Ask one 'how do you know' or 'what is likely' question."
        ),
        outcome="Child answers with an idea that is implied, not copied word-for-word.",
        success="Independent inference that is supported by the text.",
        false_positive=(
            "Repeating a stated detail, or an answer with no link to the text."
        ),
    ),
    "writing.spelling.high_frequency": _probe(
        "writing.spelling.high_frequency",
        ProbeType.PRODUCE_SAMPLE,
        task=(
            "Say one familiar 2–4 letter high-frequency word from a tiny set "
            "(the, and, you, can). Ask the child to write or spell it aloud."
        ),
        outcome="Child produces the conventional spelling of that one word.",
        success="Independent correct spelling without copying a model.",
        false_positive=(
            "Copying the word from a card already in view, or a different word."
        ),
    ),
    "writing.sentences.complete_sentence": _probe(
        "writing.sentences.complete_sentence",
        ProbeType.PRODUCE_SAMPLE,
        task="Ask the child to say or write one complete sentence about the activity.",
        outcome="The sentence has a who/what and an action.",
        success="Independent complete sentence, not a fragment or single word.",
        false_positive="A list of words, or the parent completing the sentence.",
    ),
    "writing.organization.sequence_events": _probe(
        "writing.organization.sequence_events",
        ProbeType.PRODUCE_SAMPLE,
        task="Put two or three events in order out loud or on cards.",
        outcome="Events are in a logical beginning-middle-end order.",
        success="Independent correct sequence without rearranging for the child.",
        false_positive=(
            "Naming events in random order, or the parent lining up the cards."
        ),
    ),
    "writing.organization.topic_details": _probe(
        "writing.organization.topic_details",
        ProbeType.PRODUCE_SAMPLE,
        task=(
            "Ask the child to add one supporting detail about a chosen topic "
            "(spoken or written)."
        ),
        outcome="Child adds one detail that is about that topic.",
        success="Independent on-topic detail, not a repeat of the topic word alone.",
        false_positive="An off-topic comment, or the parent supplying the detail.",
    ),
}

# Runtime guard used by integrity checks.
assert all(is_academic_code(code) for code in _PROBES)
