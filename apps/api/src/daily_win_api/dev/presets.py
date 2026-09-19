from dataclasses import dataclass

HAYES_GOAL_CODES = (
    "growth.persistence",
    "writing.organization",
    "growth.independence",
)

ALLOWED_ONBOARDING_GOAL_CODES = frozenset(
    {
        "growth.persistence",
        "growth.independence",
        "growth.communication",
        "growth.problem_solving",
        "writing.organization",
        "writing.sentences",
        "writing.spelling",
        "reading.comprehension",
        "reading.vocabulary",
        "reading.fluency",
        "math.number_sense",
        "math.addition",
        "math.subtraction",
    }
)

GOAL_CATALOG = (
    {
        "code": "growth.persistence",
        "domain_label": "Growth",
        "label": "Keep trying when something is difficult",
    },
    {
        "code": "growth.independence",
        "domain_label": "Growth",
        "label": "Do things more independently",
    },
    {
        "code": "growth.communication",
        "domain_label": "Growth",
        "label": "Explain ideas clearly",
    },
    {
        "code": "growth.problem_solving",
        "domain_label": "Growth",
        "label": "Solve problems step by step",
    },
    {
        "code": "writing.organization",
        "domain_label": "Writing",
        "label": "Organize ideas before writing",
    },
    {
        "code": "writing.sentences",
        "domain_label": "Writing",
        "label": "Build stronger sentences",
    },
    {
        "code": "writing.spelling",
        "domain_label": "Writing",
        "label": "Improve spelling",
    },
    {
        "code": "reading.comprehension",
        "domain_label": "Reading",
        "label": "Understand what was read",
    },
    {
        "code": "reading.vocabulary",
        "domain_label": "Reading",
        "label": "Build vocabulary",
    },
    {
        "code": "reading.fluency",
        "domain_label": "Reading",
        "label": "Read more smoothly",
    },
    {
        "code": "math.number_sense",
        "domain_label": "Math",
        "label": "Build number sense",
    },
    {
        "code": "math.addition",
        "domain_label": "Math",
        "label": "Practice addition",
    },
    {
        "code": "math.subtraction",
        "domain_label": "Math",
        "label": "Practice subtraction",
    },
)

ALLOWED_GRADES = frozenset({"K", "1", "2", "3", "4"})
ALLOWED_DURATIONS = frozenset({10, 15, 20, 25})
ALLOWED_RESPONSES = frozenset(
    {
        "keeps trying independently",
        "asks for help quickly",
        "becomes frustrated after an initial failure",
        "becomes frustrated after the first failure",
        "tends to avoid or stop",
        "varies / not sure",
    }
)
MAX_LABEL_LENGTH = 40
MAX_INTERESTS = 5
MAX_STRENGTHS = 5
MAX_DIFFICULTIES = 5
MAX_MOTIVATORS = 4
MIN_GOALS = 2
MAX_GOALS = 3


@dataclass(frozen=True)
class SyntheticProfile:
    key: str
    nickname: str
    age_years: int
    grade: str
    interests: tuple[str, ...]
    strengths: tuple[str, ...]
    current_difficulties: tuple[str, ...]
    motivators: tuple[str, ...]
    response_to_difficulty: str
    preferred_activity_minutes: int
    goal_codes: tuple[str, ...]


HAYES_PROFILE = SyntheticProfile(
    key="hayes",
    nickname="Hayes",
    age_years=7,
    grade="1",
    interests=("building things", "soccer", "Minecraft"),
    strengths=("math", "reading"),
    current_difficulties=(
        "writing",
        "persistence after an initial failure",
        "independent problem solving",
    ),
    motivators=(
        "competition",
        "short challenges",
        "doing activities with a caregiver",
    ),
    response_to_difficulty="becomes frustrated after the first failure",
    preferred_activity_minutes=20,
    goal_codes=HAYES_GOAL_CODES,
)

NOVA_PROFILE = SyntheticProfile(
    key="nova",
    nickname="Nova",
    age_years=8,
    grade="3",
    interests=("space", "drawing"),
    strengths=("reading",),
    current_difficulties=("organizing writing",),
    motivators=("stories/imagination", "choice"),
    response_to_difficulty="asks for help quickly",
    preferred_activity_minutes=20,
    goal_codes=("writing.organization", "growth.persistence"),
)

MILO_PROFILE = SyntheticProfile(
    key="milo",
    nickname="Milo",
    age_years=6,
    grade="1",
    interests=("dinosaurs", "soccer"),
    strengths=("communication",),
    current_difficulties=("starting independently", "number sense"),
    motivators=("movement", "short challenges"),
    response_to_difficulty="keeps trying independently",
    preferred_activity_minutes=15,
    goal_codes=("math.number_sense", "growth.independence"),
)

RILEY_PROFILE = SyntheticProfile(
    key="riley",
    nickname="Riley",
    age_years=9,
    grade="4",
    interests=("music", "building"),
    strengths=("math",),
    current_difficulties=("understanding what was read",),
    motivators=("building/making something", "choice"),
    response_to_difficulty="becomes frustrated after an initial failure",
    preferred_activity_minutes=25,
    goal_codes=("reading.comprehension", "growth.problem_solving"),
)

QA_PROFILES = (HAYES_PROFILE, NOVA_PROFILE, MILO_PROFILE, RILEY_PROFILE)

INTEREST_SUGGESTIONS = (
    "sports",
    "building",
    "drawing",
    "animals",
    "space",
    "Minecraft/games",
    "music",
    "nature",
    "stories",
    "science",
)
STRENGTH_SUGGESTIONS = (
    "math",
    "reading",
    "writing",
    "creativity",
    "communication",
    "problem solving",
    "focus",
    "independence",
)
DIFFICULTY_SUGGESTIONS = (
    "writing",
    "reading",
    "math",
    "staying focused",
    "starting independently",
    "sticking with something difficult",
    "explaining ideas",
    "organizing steps",
)
MOTIVATOR_SUGGESTIONS = (
    "competition",
    "short challenges",
    "choice",
    "building/making something",
    "movement",
    "working with a caregiver",
    "earning a small win",
    "stories/imagination",
)
GRADE_OPTIONS = (
    {"code": "K", "label": "Kindergarten"},
    {"code": "1", "label": "Grade 1"},
    {"code": "2", "label": "Grade 2"},
    {"code": "3", "label": "Grade 3"},
    {"code": "4", "label": "Grade 4"},
)
DURATION_OPTIONS = (10, 15, 20, 25)
RESPONSE_OPTIONS = (
    "keeps trying independently",
    "asks for help quickly",
    "becomes frustrated after an initial failure",
    "tends to avoid or stop",
    "varies / not sure",
)
V02_COLLECTION_FIELDS = (
    "nickname",
    "age_years",
    "grade",
    "interests",
    "strengths",
    "current_difficulties",
    "response_to_difficulty",
    "goal_codes",
    "primary_goal_code",
    "motivators",
    "preferred_activity_minutes",
)
FORBIDDEN_ONBOARDING_FIELDS = (
    "date_of_birth",
    "last_name",
    "email",
    "address",
    "school_name",
    "medical_condition",
    "diagnosis",
    "photo_url",
)
GOAL_LABEL_BY_CODE = {item["code"]: item["label"] for item in GOAL_CATALOG}


def parent_goal_label(code: str, fallback: str) -> str:
    return GOAL_LABEL_BY_CODE.get(code, fallback)
