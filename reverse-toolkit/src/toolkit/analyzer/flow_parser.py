from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class CapturedRequest:
    method: str
    path: str
    host: str
    req_headers: dict
    req_body: str
    resp_status: int
    resp_body: str
    content_type: str
    timestamp: float


def parse_flows(flows_dir: Path) -> list[CapturedRequest]:
    results = []
    for f in flows_dir.rglob("*.mitm"):
        try:
            text = f.read_text(encoding="utf-8")
            flows = json.loads(text)
            if isinstance(flows, list):
                for flow in flows:
                    req = flow.get("request", {})
                    resp = flow.get("response", {})
                    req_headers = req.get("headers", {})
                    content = req.get("content", b"")
                    if isinstance(content, bytes):
                        content = content.decode("utf-8", errors="replace")
                    resp_content = resp.get("content", b"")
                    if isinstance(resp_content, bytes):
                        resp_content = resp_content.decode("utf-8", errors="replace")
                    results.append(CapturedRequest(
                        method=req.get("method", "GET"),
                        path=req.get("path", ""),
                        host=req.get("host", ""),
                        req_headers=req_headers,
                        req_body=content,
                        resp_status=resp.get("status_code", 0),
                        resp_body=resp_content,
                        content_type=req_headers.get("Content-Type", ""),
                        timestamp=req.get("timestamp_start", 0.0)
                    ))
        except Exception:
            continue
    return results
