"""Composable filter functions for the user pipeline."""
from engine.models import User


def filter_by_gender(users: list[User], gender: str | None) -> list[User]:
    """Keep only users matching gender. If None or 'all', no filtering."""
    if gender is None or gender == "all":
        return users
    return [u for u in users if u.gender == gender]


def filter_by_rank(users: list[User], max_rank: int | None) -> list[User]:
    """Keep only users with rank <= max_rank."""
    if max_rank is None:
        return users
    return [u for u in users if u.rank <= max_rank]


def filter_by_room_type(users: list[User], room_type: str | None) -> list[User]:
    """Keep only users from specific room type ('voice' or 'video')."""
    if room_type is None or room_type == "all":
        return users
    return [u for u in users if u.room_type == room_type]


def filter_by_score(users: list[User], min_score: int | None) -> list[User]:
    """Keep only users with score >= min_score."""
    if min_score is None:
        return users
    return [u for u in users if u.score is not None and u.score >= min_score]


def filter_skip_sent(users: list[User], sent_app_uids: set[str]) -> list[User]:
    """Remove users who have already received a message."""
    return [u for u in users if u.app_uid not in sent_app_uids]


def filter_by_extra_field(users: list[User], field: str, min_value: int) -> list[User]:
    """Plugin-specific: filter by extra dict field >= min_value."""
    return [u for u in users if u.extra.get(field, 0) >= min_value]


def apply_filters(users: list[User], filter_config: dict, sent_app_uids: set[str] = None) -> list[User]:
    """Apply all configured filters in order. filter_config comes from task config JSON."""
    result = users

    result = filter_by_gender(result, filter_config.get("gender"))
    result = filter_by_rank(result, filter_config.get("rank_max"))
    result = filter_by_room_type(result, filter_config.get("room_type"))
    result = filter_by_score(result, filter_config.get("score_min"))

    if filter_config.get("skip_sent") and sent_app_uids is not None:
        result = filter_skip_sent(result, sent_app_uids)

    # Plugin-specific extra filters
    extra_filters = filter_config.get("extra", {})
    for field, min_val in extra_filters.items():
        result = filter_by_extra_field(result, field, min_val)

    return result
