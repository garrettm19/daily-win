from enum import StrEnum


class SkillDomain(StrEnum):
    MATH = "MATH"
    READING = "READING"
    WRITING = "WRITING"
    GROWTH = "GROWTH"
    LIFE = "LIFE"


class SkillStateMode(StrEnum):
    MASTERY = "mastery"
    TREND = "trend"


class SkillKind(StrEnum):
    STRAND = "strand"
    SKILL = "skill"


class AcademicBand(StrEnum):
    NOT_OBSERVED = "not_observed"
    EMERGING = "emerging"
    DEVELOPING = "developing"
    DEMONSTRATED = "demonstrated"
    RETAINED = "retained"


class AcademicResult(StrEnum):
    CORRECT_INDEPENDENTLY = "correct_independently"
    CORRECT_AFTER_LIGHT_PROMPT = "correct_after_light_prompt"
    CORRECT_AFTER_SIGNIFICANT_HELP = "correct_after_significant_help"
    INCORRECT = "incorrect"
    NOT_ATTEMPTED = "not_attempted"


class InstructionMode(StrEnum):
    INTRODUCE = "introduce"
    PRACTICE = "practice"
    REVIEW = "review"
    REMEDIATION = "remediation"
    DIAGNOSTIC = "diagnostic"


class ScaffoldLevel(StrEnum):
    HIGH = "three_step_visual"
    MEDIUM = "one_prompt"
    LOW = "independent_try"


class ProbeType(StrEnum):
    OBSERVE_INDEPENDENT_TRY = "observe_independent_try"
    COUNTED_ITEMS = "counted_items"
    RETELL = "retell"
    PRODUCE_SAMPLE = "produce_sample"


class EvidenceKind(StrEnum):
    FACT = "FACT"
    MEASUREMENT = "MEASUREMENT"
    OBSERVATION = "OBSERVATION"
    INFERENCE = "INFERENCE"


class EvidenceSource(StrEnum):
    PARENT = "PARENT"
    SYSTEM = "SYSTEM"
    ASSESSMENT = "ASSESSMENT"
    AI = "AI"
