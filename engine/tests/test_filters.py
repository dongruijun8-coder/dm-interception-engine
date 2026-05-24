"""Test filter pipeline."""
from engine.models import User
from engine.filters import apply_filters


def make_user(uid, name, gender, rank, room_type="voice", score=100):
    return User(app_uid=uid, name=name, room_id="r1", room_type=room_type,
                rank=rank, gender=gender, score=score)


def test_filter_gender():
    users = [make_user("1", "a", "male", 1), make_user("2", "b", "female", 2), make_user("3", "c", None, 3)]
    result = apply_filters(users, {"gender": "male"})
    assert len(result) == 1
    assert result[0].app_uid == "1"


def test_filter_rank():
    users = [make_user("1", "a", "male", 10), make_user("2", "b", "male", 60)]
    result = apply_filters(users, {"rank_max": 50})
    assert len(result) == 1
    assert result[0].app_uid == "1"


def test_filter_room_type():
    users = [make_user("1", "a", "male", 1, "voice"), make_user("2", "b", "male", 2, "video")]
    result = apply_filters(users, {"room_type": "voice"})
    assert len(result) == 1
    assert result[0].room_type == "voice"


def test_filter_combined():
    users = [
        make_user("1", "a", "male", 10, "voice", 500),
        make_user("2", "b", "male", 60, "voice", 500),
        make_user("3", "c", "female", 5, "voice", 500),
        make_user("4", "d", "male", 3, "video", 500),
    ]
    result = apply_filters(users, {"gender": "male", "rank_max": 50, "room_type": "voice"})
    assert len(result) == 1
    assert result[0].app_uid == "1"


def test_filter_skip_sent():
    users = [make_user("1", "a", "male", 1), make_user("2", "b", "male", 2)]
    result = apply_filters(users, {"skip_sent": True}, sent_app_uids={"1"})
    assert len(result) == 1
    assert result[0].app_uid == "2"


def test_filter_no_config():
    users = [make_user("1", "a", "male", 1), make_user("2", "b", "female", 2)]
    result = apply_filters(users, {})
    assert len(result) == 2
