import json
from datetime import datetime
from pathlib import Path
from mitmproxy import ctx


class FlowRecorder:
    def __init__(self, host_filter: str, output_dir: str):
        self.host_filter = host_filter.replace("*", "")
        self.output_dir = Path(output_dir)
        self.flows: list[dict] = []

    def _should_record(self, flow) -> bool:
        host = flow.request.pretty_host
        return self.host_filter in host

    def request(self, flow):
        if not self._should_record(flow):
            return

    def response(self, flow):
        if not self._should_record(flow):
            return

        req = flow.request
        resp = flow.response

        req_body = ""
        if req.content:
            try:
                req_body = req.content.decode("utf-8", errors="replace")
            except Exception:
                req_body = str(req.content)

        resp_body = ""
        if resp and resp.content:
            try:
                resp_body = resp.content.decode("utf-8", errors="replace")
            except Exception:
                resp_body = str(resp.content)

        headers = {}
        if req.headers:
            for k, v in req.headers.items():
                headers[k] = v

        self.flows.append({
            "request": {
                "method": req.method,
                "path": req.path,
                "host": req.pretty_host,
                "headers": headers,
                "content": req_body,
                "timestamp_start": req.timestamp_start,
            },
            "response": {
                "status_code": resp.status_code if resp else 0,
                "content": resp_body,
                "headers": dict(resp.headers) if resp and resp.headers else {},
            }
        })

    def done(self):
        if not self.flows:
            return
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        out_file = date_dir / f"flows_{ts}.mitm"
        out_file.write_text(json.dumps(self.flows, ensure_ascii=False, indent=2), encoding="utf-8")
        ctx.log.info(f"Saved {len(self.flows)} flows to {out_file}")


# mitmproxy addon entry points
addons = []
