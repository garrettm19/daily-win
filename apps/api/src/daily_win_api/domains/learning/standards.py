"""Curated static mappings. Standards are metadata, never skill identity."""

STANDARDS_SOURCE = "CCSS.ELA-Literacy / CCSS.Math"
STANDARDS_VERSION = "2010-public"

# Vendor/public identifiers only. Do not map growth/life skills.
# One public standard may legitimately span more than one Daily Win skill.
SKILL_STANDARD_REFS: tuple[dict[str, str], ...] = (
    {
        "skill_code": "math.addition.within_10",
        "standard_code": "CCSS.MATH.CONTENT.1.OA.C.6",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Fluency for addition within 10. Same identifier also covers "
            "related add/subtract-within-20 work."
        ),
    },
    {
        "skill_code": "math.addition.within_20",
        "standard_code": "CCSS.MATH.CONTENT.1.OA.C.6",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Add within 20. Distinct Daily Win skill from fluency within 10.",
    },
    {
        "skill_code": "math.addition.word_problems",
        "standard_code": "CCSS.MATH.CONTENT.1.OA.A.1",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "One-step oral 'how many in all' stories; Daily Win measures "
            "totals of 10 or less."
        ),
    },
    {
        "skill_code": "math.subtraction.within_10",
        "standard_code": "CCSS.MATH.CONTENT.1.OA.C.6",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Fluency for subtraction within 10. Same identifier as addition "
            "within 10/20 by design of the standard."
        ),
    },
    {
        "skill_code": "math.subtraction.within_20",
        "standard_code": "CCSS.MATH.CONTENT.1.OA.C.6",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Subtract within 20. Was previously unmapped.",
    },
    {
        "skill_code": "math.number_sense.counting",
        "standard_code": "CCSS.MATH.CONTENT.K.CC.B.5",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Count up to 10 objects with one-to-one correspondence.",
    },
    {
        "skill_code": "math.number_sense.compare",
        "standard_code": "CCSS.MATH.CONTENT.K.CC.C.6",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Compare two groups of 10 or fewer by matching or counting.",
    },
    {
        "skill_code": "math.multiplication.equal_groups",
        "standard_code": "CCSS.MATH.CONTENT.3.OA.A.1",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Interpret products as equal groups. Daily Win measures 2–3 groups of "
            "≤5 objects, not times-table fluency. Age band is 8–9 to match Grade 3."
        ),
    },
    {
        "skill_code": "math.fractions.halves_fourths",
        "standard_code": "CCSS.MATH.CONTENT.1.G.A.3",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Grade 1 partition language; Daily Win asks the child to identify "
            "a half and a fourth of an already-split whole."
        ),
    },
    {
        "skill_code": "reading.phonics.letter_sounds",
        "standard_code": "CCSS.ELA-LITERACY.RF.K.3.A",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Produce the primary sound, not the letter name.",
    },
    {
        "skill_code": "reading.phonics.blend_cvc",
        "standard_code": "CCSS.ELA-LITERACY.RF.1.2.B",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Orally blend three phonemes into a CVC word.",
    },
    {
        "skill_code": "reading.fluency.smooth_oral",
        "standard_code": "CCSS.ELA-LITERACY.RF.1.4",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Read a 6–8 word familiar sentence from print; not a full passage "
            "fluency score."
        ),
    },
    {
        "skill_code": "reading.vocabulary.context_clues",
        "standard_code": "CCSS.ELA-LITERACY.L.2.4.A",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Use context in one spoken sentence; not dictionary or "
            "multi-paragraph clues."
        ),
    },
    {
        "skill_code": "reading.comprehension.recall_details",
        "standard_code": "CCSS.ELA-LITERACY.RL.1.1",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Answer one detail question after a short read-aloud.",
    },
    {
        "skill_code": "reading.comprehension.main_idea",
        "standard_code": "CCSS.ELA-LITERACY.RI.1.2",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "State what a short passage is mostly about.",
    },
    {
        "skill_code": "reading.comprehension.simple_inference",
        "standard_code": "CCSS.ELA-LITERACY.RL.2.1",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": (
            "Grade 2 ask-and-answer; Daily Win uses 1–2 sentences and one "
            "implied question. Age 7–9 is intentional."
        ),
    },
    {
        "skill_code": "writing.sentences.complete_sentence",
        "standard_code": "CCSS.ELA-LITERACY.L.1.1.J",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Produce one complete simple sentence.",
    },
    {
        "skill_code": "writing.organization.sequence_events",
        "standard_code": "CCSS.ELA-LITERACY.W.1.3",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Order two or three events; not a full narrative.",
    },
    {
        "skill_code": "writing.organization.topic_details",
        "standard_code": "CCSS.ELA-LITERACY.W.1.2",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Add one on-topic supporting detail.",
    },
    {
        "skill_code": "writing.spelling.high_frequency",
        "standard_code": "CCSS.ELA-LITERACY.L.1.2.D",
        "source": STANDARDS_SOURCE,
        "version": STANDARDS_VERSION,
        "note": "Spell one 2–4 letter high-frequency word, not a full word list.",
    },
)
