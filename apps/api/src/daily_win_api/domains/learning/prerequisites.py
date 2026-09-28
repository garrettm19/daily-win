from daily_win_api.domains.learning.taxonomy import definition_by_code

PREREQUISITE_EDGES: tuple[tuple[str, str], ...] = (
    ("math.number_sense.counting", "math.number_sense.compare"),
    ("math.number_sense.counting", "math.addition.within_10"),
    ("math.addition.within_10", "math.addition.within_20"),
    ("math.addition.within_20", "math.addition.word_problems"),
    ("math.addition.within_10", "math.subtraction.within_10"),
    ("math.subtraction.within_10", "math.subtraction.within_20"),
    ("math.addition.within_10", "math.multiplication.equal_groups"),
    ("reading.phonics.letter_sounds", "reading.phonics.blend_cvc"),
    ("reading.phonics.blend_cvc", "reading.fluency.smooth_oral"),
    ("reading.phonics.blend_cvc", "writing.spelling.cvc"),
    ("reading.phonics.blend_cvc", "writing.spelling.high_frequency"),
    ("writing.spelling.cvc", "writing.spelling.patterns"),
    ("writing.spelling.patterns", "writing.spelling.endings_suffixes"),
    ("writing.spelling.endings_suffixes", "writing.spelling.multisyllabic_irregular"),
    ("reading.comprehension.recall_details", "reading.comprehension.main_idea"),
    ("reading.comprehension.main_idea", "reading.comprehension.simple_inference"),
    ("writing.sentences.complete_sentence", "writing.organization.sequence_events"),
    ("writing.organization.sequence_events", "writing.organization.topic_details"),
)


def prerequisites_for(skill_code: str) -> tuple[str, ...]:
    return tuple(src for src, dest in PREREQUISITE_EDGES if dest == skill_code)


def dependents_for(skill_code: str) -> tuple[str, ...]:
    return tuple(dest for src, dest in PREREQUISITE_EDGES if src == skill_code)


def has_cycle(edges: tuple[tuple[str, str], ...] = PREREQUISITE_EDGES) -> bool:
    graph: dict[str, list[str]] = {}
    for src, dest in edges:
        graph.setdefault(src, []).append(dest)
        graph.setdefault(dest, [])
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(dfs(node) for node in graph)


def assert_prerequisites_valid() -> None:
    catalog = definition_by_code()
    for src, dest in PREREQUISITE_EDGES:
        if src not in catalog or dest not in catalog:
            raise ValueError(f"unknown_prerequisite_skill:{src}->{dest}")
        if src == dest:
            raise ValueError(f"self_prerequisite:{src}")
    if has_cycle():
        raise ValueError("prerequisite_cycle")
