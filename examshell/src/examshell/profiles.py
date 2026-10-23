"""Local profile and grading-mode configuration.

The lookup functions form the boundary for a future API backed by user and exam
configuration. The local profiles intentionally share the Rank 02 exercise bank.
"""

from dataclasses import dataclass

from examshell.catalog import EXERCISES, Exercise


@dataclass(frozen=True)
class ExamMode:
    name: str
    advance_on_failure: bool
    exercises: tuple[Exercise, ...]


@dataclass(frozen=True)
class UserProfile:
    login: str
    mode: str


EXAM_MODES = {
    "trial": ExamMode(name="trial", advance_on_failure=True, exercises=EXERCISES),
    "normal": ExamMode(name="normal", advance_on_failure=False, exercises=EXERCISES),
}

USER_PROFILES = {
    "trial": UserProfile(login="trial", mode="trial"),
    "normal": UserProfile(login="normal", mode="normal"),
}


def get_user_profile(login: str) -> UserProfile | None:
    """Resolve a local test login; replace with an API-backed lookup later."""
    return USER_PROFILES.get(login.strip().lower())


def get_exam_mode(mode: str) -> ExamMode:
    """Return the exam policy and exercise bank for a profile."""
    return EXAM_MODES[mode]
