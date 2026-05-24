import json
from dataclasses import asdict
from toolkit.schema import (
    ApiSpec, AuthInfo, LoginStep, CommonParams,
    EndpointDef, PreStep, AntiReverseInfo
)

def test_api_spec_roundtrip():
    """ApiSpec 可以序列化为 JSON 并反序列化回来"""
    spec = ApiSpec(
        app="popo",
        version="1.7.40",
        base_url="https://api.pp.weimipopo.com",
        auth=AuthInfo(
            type="token",
            login_flow=[
                LoginStep(order=1, endpoint="/sms", method="POST",
                          params={"phone": "string"}, extract="smsCode"),
                LoginStep(order=2, endpoint="/login", method="POST",
                          params={"phone": "string", "smsCode": "string"}, extract=None),
            ]
        ),
        common_params=CommonParams(
            headers={"User-Agent": "okhttp/3.14.9"},
            body=["app", "build", "channel", "meid", "token", "uid", "version"],
            url_params=[]
        ),
        endpoints=[
            EndpointDef(
                name="room_list",
                method="POST",
                path="/plpl/room/main/listByCat",
                category="rooms",
                params={"catId": 1, "limit": 20, "offset": 0},
                pagination="offset_limit",
                response_model="rooms[]",
                pre_steps=None
            ),
            EndpointDef(
                name="send_message",
                method="POST",
                path="/plpl/relation/in/chat/send",
                category="message",
                params={},
                pagination=None,
                response_model=None,
                pre_steps=[
                    PreStep(endpoint="/plpl/relation/get/user/in/chat", extract="tid", pass_to="tid"),
                    PreStep(endpoint="/plpl/pr/chat/preCheck", extract="msgChatId", pass_to="msgChatId"),
                ]
            ),
        ],
        status_codes={"S_OK": "成功", "F_BAN": "封禁"},
        anti_reverse=AntiReverseInfo(
            ssl_pinning=True,
            encryption="AES/CBC/PKCS5 (手机号字段)",
            device_fingerprint="MEID + IMEI",
            captcha="网易易盾",
            notes="richLevel < 6 无法私信"
        )
    )
    d = asdict(spec)
    json_str = json.dumps(d, ensure_ascii=False, indent=2)
    loaded = json.loads(json_str)
    assert loaded["app"] == "popo"
    assert loaded["auth"]["type"] == "token"
    assert len(loaded["auth"]["login_flow"]) == 2
    assert loaded["auth"]["login_flow"][0]["extract"] == "smsCode"
    assert loaded["auth"]["login_flow"][1]["extract"] is None
    assert len(loaded["endpoints"]) == 2
    assert loaded["endpoints"][0]["category"] == "rooms"
    assert loaded["endpoints"][1]["pre_steps"][0]["extract"] == "tid"
    assert loaded["status_codes"]["S_OK"] == "成功"
    assert loaded["anti_reverse"]["ssl_pinning"] is True
