from toolkit.generator.scaffold import generate

def test_generate_plugin_and_models():
    spec = {
        "app": "popo",
        "base_url": "https://api.pp.weimipopo.com",
        "auth": {"type": "token", "login_flow": [
            {"order": 1, "endpoint": "/sms", "method": "POST", "params": {"phone": "string"}, "extract": None}
        ]},
        "endpoints": [
            {"name": "room_list", "method": "POST", "path": "/room/list",
             "category": "rooms", "params": {"catId": "int"},
             "pagination": "offset_limit", "response_model": "rooms[]", "pre_steps": None},
            {"name": "send_message", "method": "POST", "path": "/chat/send",
             "category": "message", "params": {},
             "pagination": None, "response_model": None,
             "pre_steps": [{"endpoint": "/chat/pre", "extract": "tid", "pass_to": "tid"}]},
        ],
        "status_codes": {"S_OK": ""},
        "anti_reverse": {"ssl_pinning": False, "encryption": "none",
                         "device_fingerprint": "none", "captcha": "none", "notes": ""}
    }
    plugin_code, models_code = generate(spec)

    assert "class PopoPlugin" in plugin_code
    assert "def authenticate" in plugin_code
    assert "def fetch_rooms" in plugin_code
    assert "def fetch_users" in plugin_code
    assert "def send_message" in plugin_code
    assert "def check_account_health" in plugin_code
    assert "BasePlugin" in plugin_code
    assert "https://api.pp.weimipopo.com" in plugin_code

    assert "class Room" in models_code or "Room" in models_code
