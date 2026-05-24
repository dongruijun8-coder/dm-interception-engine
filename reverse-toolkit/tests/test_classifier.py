from toolkit.analyzer.classifier import classify
from toolkit.analyzer.endpoint_extractor import ExtractedEndpoint


def make_ep(path, method="POST", host="api.example.com"):
    return ExtractedEndpoint(
        method=method, path=path, host=host,
        content_type="application/json"
    )


def test_classify_auth():
    eps = [make_ep("/api/v1/login"), make_ep("/api/v1/register"), make_ep("/sms/send")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "auth"


def test_classify_rooms():
    eps = [make_ep("/room/list"), make_ep("/live/hot"), make_ep("/category/live")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "rooms"


def test_classify_rank():
    eps = [make_ep("/rank/weekly"), make_ep("/contribute/list"), make_ep("/leaderboard/top")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "rank"


def test_classify_message():
    eps = [make_ep("/chat/send"), make_ep("/message/inbox"), make_ep("/im/thread")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "message"


def test_classify_profile():
    eps = [make_ep("/user/profile"), make_ep("/user/info"), make_ep("/card/detail")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "profile"


def test_classify_other_fallback():
    eps = [make_ep("/config/get"), make_ep("/health/check")]
    result = classify(eps)
    for ep in result:
        assert ep["category"] == "other"
