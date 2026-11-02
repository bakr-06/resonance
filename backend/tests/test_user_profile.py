from datetime import date

from db.models import SocialStatus
from services.user_profile import (
    UserProfile,
    build_user_profile,
    calculate_age,
    compose_system_prompt,
    render_user_profile,
)


def test_age_is_complete_on_the_birthday_itself() -> None:
    assert calculate_age(date(2006, 3, 9), today=date(2026, 3, 9)) == 20


def test_age_is_not_complete_the_day_before_the_birthday() -> None:
    assert calculate_age(date(2006, 3, 9), today=date(2026, 3, 8)) == 19


def test_february_29_birthday_advances_on_march_first_in_common_years() -> None:
    assert calculate_age(date(2004, 2, 29), today=date(2025, 2, 28)) == 20
    assert calculate_age(date(2004, 2, 29), today=date(2025, 3, 1)) == 21


def test_future_birth_date_never_produces_a_negative_age() -> None:
    assert calculate_age(date(2030, 1, 1), today=date(2026, 1, 1)) == 0


def test_profile_carries_the_derived_age_and_enum_status() -> None:
    profile = build_user_profile(
        name="Bakr",
        social_status=SocialStatus.SINGLE,
        date_of_birth=date(2006, 3, 9),
        today=date(2026, 3, 9),
    )

    assert profile == UserProfile(
        name="Bakr",
        age=20,
        social_status=SocialStatus.SINGLE,
    )


def test_rendered_profile_uses_the_enum_value_not_its_name() -> None:
    profile = build_user_profile(
        name="Bakr",
        social_status=SocialStatus.SINGLE,
        date_of_birth=date(2006, 3, 9),
        today=date(2026, 3, 9),
    )

    rendered: str = render_user_profile(profile)

    assert "Name: Bakr" in rendered
    assert "Age: 20" in rendered
    assert "Social status: single" in rendered
    assert "SocialStatus" not in rendered


def test_compose_keeps_the_base_prompt_first() -> None:
    profile = UserProfile(name="Bakr", age=20, social_status=SocialStatus.SINGLE)

    composed: str | None = compose_system_prompt("base prompt", profile)

    assert composed is not None
    assert composed.startswith("base prompt")
    assert "Name: Bakr" in composed


def test_compose_without_a_profile_returns_the_base_prompt_unchanged() -> None:
    assert compose_system_prompt("base prompt", None) == "base prompt"


def test_compose_without_a_base_prompt_returns_only_the_profile() -> None:
    profile = UserProfile(name="Bakr", age=20, social_status=SocialStatus.SINGLE)

    composed: str | None = compose_system_prompt(None, profile)

    assert composed is not None
    assert composed.startswith("About the person you are talking to")


def test_compose_returns_none_when_there_is_nothing_to_say() -> None:
    assert compose_system_prompt(None, None) is None
    assert compose_system_prompt("   ", None) is None
