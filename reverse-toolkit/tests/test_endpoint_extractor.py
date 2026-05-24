from toolkit.analyzer.endpoint_extractor import extract_endpoints, ExtractedEndpoint
from toolkit.analyzer.flow_parser import CapturedRequest

def make_req(method="POST", path="/api/test", host="api.example.com",
             req_body='{"a":1}', resp_body='{"data":[]}', resp_status=200,
             content_type="application/json"):
    return CapturedRequest(
        method=method, path=path, host=host,
        req_headers={}, req_body=req_body,
        resp_status=resp_status, resp_body=resp_body,
        content_type=content_type, timestamp=0.0
    )

def test_dedup_same_path():
    reqs = [make_req(path="/api/rooms/list") for _ in range(3)]
    eps = extract_endpoints(reqs)
    assert len(eps) == 1
    assert eps[0].method == "POST"
    assert eps[0].path == "/api/rooms/list"

def test_preserves_params_from_first_seen():
    reqs = [
        make_req(path="/api/search", req_body='{"q":"hello","limit":20}'),
        make_req(path="/api/search", req_body='{"q":"world","limit":50}'),
    ]
    eps = extract_endpoints(reqs)
    assert len(eps) == 1
    assert "q" in eps[0].sample_params

def test_sorts_by_path():
    reqs = [make_req(path=p) for p in ["/zzz", "/aaa", "/mmm"]]
    eps = extract_endpoints(reqs)
    paths = [e.path for e in eps]
    assert paths == sorted(paths)

def test_ignores_static_resources():
    reqs = [
        make_req(path="/api/users", content_type="application/json"),
        make_req(path="/favicon.ico", content_type="image/x-icon"),
        make_req(path="/static/app.js", content_type="application/javascript"),
        make_req(path="/styles/main.css", content_type="text/css"),
    ]
    eps = extract_endpoints(reqs)
    paths = [e.path for e in eps]
    assert "/favicon.ico" not in paths
    assert "/static/app.js" not in paths
