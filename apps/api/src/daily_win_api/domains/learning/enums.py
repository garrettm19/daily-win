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
