from toolkit.analyzer.endpoint_extractor import ExtractedEndpoint

CATEGORY_RULES = {
    "auth":     ["/login", "/register", "/sms", "/token", "/auth", "/signin", "/signup"],
    "rank":     ["/rank", "/contribute", "/leaderboard", "/top", "/gift"],
    "rooms":    ["/list", "/hot", "/category", "/room", "/live", "/search"],
    "message":  ["/chat", "/send", "/message", "/inbox", "/im", "/conversation"],
    "profile":  ["/user", "/profile", "/info", "/card", "/account"],
}


def classify(endpoints: list[ExtractedEndpoint]) -> list[dict]:
    result = []
    for ep in endpoints:
        category = _classify_one(ep.path.lower(), ep.method.lower(), ep.host.lower())
        result.append({
            "method": ep.method,
            "path": ep.path,
            "host": ep.host,
            "category": category,
            "content_type": ep.content_type,
            "sample_params": ep.sample_params,
            "sample_response": ep.sample_response,
            "hit_count": ep.hit_count,
        })
    return result


def _classify_one(path: str, method: str, host: str) -> str:
    for cat, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in path:
                return cat
    return "other"
