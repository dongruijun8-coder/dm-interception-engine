import json
from toolkit.schema import ApiSpec, AuthInfo, CommonParams, EndpointDef, AntiReverseInfo
from toolkit.analyzer.flow_parser import CapturedRequest


def build_spec(app: str, classified_endpoints: list[dict], requests: list[CapturedRequest]) -> ApiSpec:
    host = requests[0].host if requests else ""
    base_url = f"https://{host}"

    common_body = list(detect_common_params(requests))
    common_headers = detect_common_headers(requests)

    status_codes = detect_status_codes(requests)

    endpoints = []
    for ep in classified_endpoints:
        endpoints.append(EndpointDef(
            name=_derive_name(ep["path"]),
            method=ep["method"],
            path=ep["path"],
            category=ep["category"],
            params=ep["sample_params"],
            pagination=_detect_pagination(ep),
            response_model=None,
            pre_steps=None
        ))

    return ApiSpec(
        app=app,
        version="",
        base_url=base_url,
        auth=AuthInfo(type="token"),
        common_params=CommonParams(headers=common_headers, body=common_body),
        endpoints=endpoints,
        status_codes=status_codes,
        anti_reverse=AntiReverseInfo()
    )


def detect_common_params(requests: list[CapturedRequest]) -> set[str]:
    if not requests:
        return set()
    parsed_bodies = []
    for r in requests:
        try:
            d = json.loads(r.req_body)
            if isinstance(d, dict):
                parsed_bodies.append(d)
        except (json.JSONDecodeError, ValueError):
            continue
    if not parsed_bodies:
        return set()
    threshold = len(parsed_bodies) // 2 + 1
    all_keys = set()
    for body in parsed_bodies:
        all_keys.update(body.keys())
    common = set()
    for key in all_keys:
        count = sum(1 for b in parsed_bodies if key in b)
        if count >= threshold:
            common.add(key)
    return common


def detect_common_headers(requests: list[CapturedRequest]) -> dict[str, str]:
    if not requests:
        return {}
    for r in requests:
        h = r.req_headers
        if h:
            return {k: v for k, v in h.items()
                    if k.lower() not in ("host", "content-length", "content-type", "accept-encoding")}
    return {}


def detect_status_codes(requests: list[CapturedRequest]) -> dict[str, str]:
    codes: dict[str, int] = {}
    for r in requests:
        try:
            d = json.loads(r.resp_body)
            if isinstance(d, dict) and "status" in d:
                s = d["status"]
                codes[s] = codes.get(s, 0) + 1
        except (json.JSONDecodeError, ValueError):
            continue
    return {k: "" for k in codes if codes[k] >= 1}


def _derive_name(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.isdigit()]
    if len(parts) >= 2:
        return "_".join(parts[-2:])
    return parts[-1] if parts else "unknown"


def _detect_pagination(ep: dict) -> str | None:
    params = ep.get("sample_params", {})
    param_keys = set(params.keys())
    if {"offset", "limit"}.issubset(param_keys):
        return "offset_limit"
    if {"page", "pageSize"}.issubset(param_keys) or {"pageNum", "pageSize"}.issubset(param_keys):
        return "page_num"
    if "cursor" in param_keys:
        return "cursor"
    return None
