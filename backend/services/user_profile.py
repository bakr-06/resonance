"""Turn the user's stored identity into background context for the model.

The profile is deliberately kept out of the message log: it is not a turn in
the conversation, it does not change while a session is running, and putting
it in the window would spend a context slot and be duplicated as the window
slides. It belongs in the system prompt, which ``_build_messages`` already
reserves inside the character budget.
"""

from dataclasses import dataclass
from datetime import date

from db.models import SocialStatus


@dataclass(frozen=True)
class UserProfile:
    """The identity facts the model is allowed to see.

    ``age`` is derived from the stored date of birth on every request instead
    of being stored itself, so it can never go stale.
    """

    name: str
    age: int
    social_status: SocialStatus


def calculate_age(date_of_birth: date, today: date | None = None) -> int:
    """Return the number of completed years between birth and ``today``.

    ``today`` is injectable so tests can pin the reference date. Someone born
    on 29 February gains a year on 1 March in non-leap years, which matches
    the usual legal convention.
    """
    reference: date = date.today() if today is None else today
    has_had_birthday: bool = (reference.month, reference.day) >= (
        date_of_birth.month,
        date_of_birth.day,
    )
    age: int = reference.year - date_of_birth.year - (0 if has_had_birthday else 1)

    # The API rejects future birth dates, but a corrupted row must not produce
    # a negative age in the prompt.
    return max(age, 0)


def build_user_profile(
        name: str,
        social_status: SocialStatus,
        date_of_birth: date,
        today: date | None = None,
) -> UserProfile:
    """Collect the profile from raw user fields so callers need no ORM model."""
    return UserProfile(
        name=name,
        age=calculate_age(date_of_birth, today),
        social_status=social_status,
    )


def render_user_profile(profile: UserProfile) -> str:
    """Render the profile as the block the model reads in its system prompt."""
    return (
        "About the person you are talking to:\n"
        f"- Name: {profile.name}\n"
        f"- Age: {profile.age}\n"
        f"- Social status: {profile.social_status.value}\n"
        "Use these details only when they are relevant to the conversation. "
        "Do not repeat them back to the person."
    )


def compose_system_prompt(
        system_prompt: str | None,
        profile: UserProfile | None,
) -> str | None:
    """Append the profile block to the base system prompt.

    Returns ``None`` only when there is neither a base prompt nor a profile,
    so "no system message" still passes through unchanged. The base prompt
    stays first because it sets the behaviour; the profile is only background
    facts that must not override it.
    """
    parts: list[str] = []
    if system_prompt and system_prompt.strip():
        parts.append(system_prompt)
    if profile is not None:
        parts.append(render_user_profile(profile))

    if not parts:
        return None
    return "\n\n".join(parts)
