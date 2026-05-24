from toolkit.analyzer.spec_builder import build_spec, detect_common_params, detect_status_codes
from toolkit.analyzer.flow_parser import CapturedRequest
from toolkit.analyzer.endpoint_extractor import extract_endpoints
from toolkit.analyzer.classifier import classify

def test_build_spec_structure():
    reqs = [
        CapturedRequest(method="POST", path="/api/login", host="api.example.com",
                        req_headers={"Authorization": "Bearer xxx"},
                        req_body='{"phone":"13800138000","token":"abc"}',
                        resp_status=200, resp_body='{"status":"S_OK"}',
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/room/list", host="api.example.com",
                        req_headers={"Authorization": "Bearer xxx"},
                        req_body='{"catId":1,"token":"abc","limit":20}',
                        resp_status=200, resp_body='{"status":"S_OK","data":[]}',
                        content_type="application/json", timestamp=0.0),
    ]
    eps = extract_endpoints(reqs)
    classified = classify(eps)
    spec = build_spec("testapp", classified, reqs)
    assert spec.app == "testapp"
    assert spec.base_url == "https://api.example.com"
    assert len(spec.endpoints) == 2
    assert spec.status_codes == {"S_OK": ""}

def test_detect_common_params():
    reqs = [
        CapturedRequest(method="POST", path="/api/a", host="api.example.com",
                        req_headers={}, req_body='{"a":1,"b":2,"c":3}',
                        resp_status=200, resp_body="{}",
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/b", host="api.example.com",
                        req_headers={}, req_body='{"a":10,"b":20,"d":40}',
                        resp_status=200, resp_body="{}",
                        content_type="application/json", timestamp=0.0),
    ]
    common = detect_common_params(reqs)
    assert "a" in common
    assert "b" in common
    assert "c" not in common

def test_detect_status_codes():
    reqs = [
        CapturedRequest(method="POST", path="/api/a", host="api.example.com",
                        req_headers={}, req_body="{}",
                        resp_status=200, resp_body='{"status":"S_OK"}',
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/b", host="api.example.com",
                        req_headers={}, req_body="{}",
                        resp_status=200, resp_body='{"status":"F_BAN"}',
                        content_type="application/json", timestamp=0.0),
        CapturedRequest(method="POST", path="/api/c", host="api.example.com",
                        req_headers={}, req_body="{}",
                        resp_status=200, resp_body='{"status":"F_BAN"}',
                        content_type="application/json", timestamp=0.0),
    ]
    codes = detect_status_codes(reqs)
    assert "S_OK" in codes
    assert "F_BAN" in codes
