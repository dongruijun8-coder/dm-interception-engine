from toolkit.generator.scaffold import generate


def test_generate_plugin_and_models():
    spec = {
        "app": "popo",
        "base_url": "https://api.pp.weimipopo.com",
        "common_params": {
            "headers": {"User-Agent": "okhttp/3.14.9"},
            "body": ["app", "build", "channel", "token", "uid", "version"]
        },
        "auth": {"type": "token", "login_flow": [
            {"order": 1, "endpoint": "/sms", "method": "POST",
             "params": {"phone": "string"}, "extract": None},
            {"order": 2, "endpoint": "/login", "method": "POST",
             "params": {"phone": "string", "smsCode": "string"}, "extract": "token"},
        ]},
        "endpoints": [
            {"name": "room_list", "method": "POST", "path": "/room/list",
             "category": "rooms", "params": {"catId": "int"},
             "pagination": "offset_limit", "response_model": "rooms[]", "pre_steps": None},
            {"name": "send_message", "method": "POST", "path": "/chat/send",
             "category": "message", "params": {},
             "pagination": None, "response_model": None,
             "pre_steps": [
                 {"endpoint": "/chat/pre", "extract": "tid", "pass_to": "tid"},
                 {"endpoint": "/chat/preCheck", "extract": "msgChatId", "pass_to": "msgChatId"},
             ]},
            {"name": "user_rank", "method": "POST", "path": "/room/rank/list",
             "category": "rank", "params": {"period": "WEEKLY"},
             "pagination": "offset_limit", "response_model": "users[]", "pre_steps": None},
        ],
        "status_codes": {"S_OK": "成功", "F_BAN": "封禁"},
        "anti_reverse": {"ssl_pinning": False, "encryption": "none",
                         "device_fingerprint": "none", "captcha": "none", "notes": ""}
    }
    plugin_code, models_code = generate(spec)

    # class and method signatures
    assert "class PopoPlugin" in plugin_code
    assert "BasePlugin" in plugin_code
    assert "def authenticate" in plugin_code
    assert "def fetch_rooms" in plugin_code
    assert "def fetch_users" in plugin_code
    assert "def send_message" in plugin_code
    assert "def check_account_health" in plugin_code
    assert "https://api.pp.weimipopo.com" in plugin_code

    # generates real HTTP calls, not TODOs
    assert "requests.post" in plugin_code
    assert "import requests" in plugin_code
    assert "# Step 1:" in plugin_code
    assert "# Step 2:" in plugin_code
    assert "self._post" in plugin_code
    assert "self._paginate" in plugin_code
    assert "self._build_body" in plugin_code
    assert "credential.get" in plugin_code

    # pre-steps are generated
    assert "pre1 =" in plugin_code
    assert "pre2 =" in plugin_code
    assert '"tid"' in plugin_code
    assert '"msgChatId"' in plugin_code

    # models
    assert "class Room" in models_code
    assert "class User" in models_code
