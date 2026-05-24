from dataclasses import dataclass, field
from toolkit.analyzer.flow_parser import CapturedRequest
import json

STATIC_EXTENSIONS = {".js", ".css", ".png", ".jpg", ".gif", ".svg", ".ico",
                     ".woff", ".woff2", ".ttf", ".map", ".webp", ".mp4"}


@dataclass
class ExtractedEndpoint:
    method: str
    path: str
    host: str
    content_type: str
    sample_params: dict = field(default_factory=dict)
    sample_response: str = ""
    hit_count: int = 1


def extract_endpoints(requests: list[CapturedRequest]) -> list[ExtractedEndpoint]:
    seen: dict[str, ExtractedEndpoint] = {}

    for req in requests:
        if _is_static(req.path, req.content_type):
            continue

        key = f"{req.method}:{req.host}:{req.path}"
        if key in seen:
            seen[key].hit_count += 1
            continue

        params = _extract_params(req.req_body, req.content_type)
        ep = ExtractedEndpoint(
            method=req.method,
            path=req.path,
            host=req.host,
            content_type=req.content_type,
            sample_params=params,
            sample_response=req.resp_body[:500],
        )
        seen[key] = ep

    return sorted(seen.values(), key=lambda e: e.path)


def _is_static(path: str, content_type: str) -> bool:
    for ext in STATIC_EXTENSIONS:
        if path.lower().endswith(ext):
            return True
    static_cts = ["image/", "text/css", "font/", "video/", "audio/"]
    for ct in static_cts:
        if content_type.startswith(ct):
            return True
    return False


def _extract_params(body: str, content_type: str) -> dict:
    if not body:
        return {}
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            return {k: type(v).__name__ for k, v in data.items()}
    except (json.JSONDecodeError, ValueError):
        pass
    return {}
