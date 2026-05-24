from pathlib import Path
from toolkit.analyzer.flow_parser import parse_flows, CapturedRequest
import json


def test_parse_flows_from_dir(tmp_path):
    """解析目录中的 .mitm 文件"""
    dump_dir = tmp_path / "raw_flows" / "2026-05-19"
    dump_dir.mkdir(parents=True)

    sample_flow = {
        "request": {
            "method": "POST",
            "path": "/plpl/room/main/listByCat",
            "host": "api.pp.weimipopo.com",
            "headers": {"Content-Type": "application/json"},
            "content": '{"catId":1,"limit":20}',
            "timestamp_start": 1716100000.0
        },
        "response": {
            "status_code": 200,
            "content": '{"data":{"rooms":[]}}',
            "headers": {"Content-Type": "application/json"}
        }
    }
    (dump_dir / "flows.mitm").write_text(json.dumps([sample_flow]), encoding="utf-8")

    requests = parse_flows(dump_dir)
    assert len(requests) >= 1
    req = requests[0]
    assert req.method == "POST"
    assert req.host == "api.pp.weimipopo.com"
    assert "/plpl/room" in req.path
