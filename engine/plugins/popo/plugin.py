"""Popo (漂漂) plugin — dual‑zone (voice + video) live‑streaming platform."""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from engine.plugin_base import BasePlugin
from engine.models import (
    AuthResult,
    Room,
    User,
    Message,
    SendResult,
    HealthStatus,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://api.pp.weimipopo.com"
USER_AGENT = "okhttp/3.14.9"

# Video live category IDs to paginate through
VIDEO_CAT_IDS = [1, 4, 5, 7, 17]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _common_body(session: dict) -> dict:
    """Return the request envelope fields shared by every Popo API call."""
    return {
        "app": "plpl",
        "build": 126,
        "channel": "plpl_baidu",
        "meid": session.get("meid", ""),
        "device": "SM-S9210",
        "platform": "Android",
        "subChannel": "",
        "token": session.get("token", ""),
        "uid": session.get("uid", ""),
        "version": "1.7.40",
        "patchVersion": "",
        "sysVersion": "12",
    }


def _build_body(session: dict, params: dict | None = None, **extra) -> dict:
    """Assemble a full request body from the common fields + optional params + extra keys."""
    body = _common_body(session)
    if params is not None:
        body["params"] = params
    body.update(extra)
    return body


async def _post(
    client: httpx.AsyncClient,
    path: str,
    session: dict,
    params: dict | None = None,
    **extra,
) -> dict:
    """POST to the Popo API and return the parsed JSON body."""
    url = f"{BASE_URL}{path}"
    body = _build_body(session, params, **extra)
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json; charset=utf-8",
    }
    resp = await client.post(url, json=body, headers=headers)
    resp.raise_for_status()
    return resp.json()


def _is_success(data: dict) -> bool:
    return data.get("code") == "S_OK"


def _get_data(data: dict) -> dict:
    return data.get("data", {}) or {}


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------

class PopoPlugin(BasePlugin):
    """Plugin for 漂漂 (Popo Live) — dual-zone voice + video platform."""

    app_name: str = "popo"

    # ------------------------------------------------------------------
    # authenticate
    # ------------------------------------------------------------------
    async def authenticate(self, credential: dict) -> AuthResult:
        """Login via phone + smsCode.

        credential dict requires:
          - phone  (str)
          - smsCode (str)
        Optional:
          - meid   (str) — device ID, random 14‑char hex if absent
        """
        phone = credential.get("phone", "")
        sms_code = credential.get("smsCode", "")
        if not phone or not sms_code:
            return AuthResult(success=False, error="Missing 'phone' or 'smsCode' in credential")

        meid = credential.get("meid", "") or _random_meid()

        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1 — get associated account list (to obtain tid)
            step1 = await _post(
                client,
                "/plpl/ptl/relation/account/list",
                {"meid": meid, "token": "", "uid": ""},
                params={"phone": phone, "smsCode": sms_code},
            )
            if not _is_success(step1):
                return AuthResult(
                    success=False,
                    error=f"account/list failed: {step1.get('code')} {step1.get('message','')}",
                )
            accounts = _get_data(step1).get("list", [])
            if not accounts:
                return AuthResult(success=False, error="No accounts associated with this phone")

            tid = accounts[0].get("uid", "")
            if not tid:
                return AuthResult(success=False, error="No uid in account list response")

            # Step 2 — login
            step2 = await _post(
                client,
                "/plpl/ptl/login/relation/account",
                {"meid": meid, "token": "", "uid": ""},
                phone=phone,
                smsCode=sms_code,
                tid=tid,
                imei=meid,
            )
            if not _is_success(step2):
                return AuthResult(
                    success=False,
                    error=f"login failed: {step2.get('code')} {step2.get('message','')}",
                )

            data = _get_data(step2)
            token = data.get("token", "")
            full_user = data.get("fullUser", {})
            uid = full_user.get("uid", "") or str(tid)

            if not token:
                return AuthResult(success=False, error="No token in login response")

            return AuthResult(
                success=True,
                session={
                    "phone": phone,
                    "smsCode": sms_code,
                    "meid": meid,
                    "token": token,
                    "uid": uid,
                    "raw": data,
                },
            )

    # ------------------------------------------------------------------
    # fetch_rooms
    # ------------------------------------------------------------------
    async def fetch_rooms(self, session: dict, filters: dict) -> list[Room]:
        """Fetch all voice and video rooms.

        Pagination is handled internally.  Voice rooms come from listByCat
        (catId=1); video rooms come from category/live for several
        category IDs.
        """
        rooms: list[Room] = []
        async with httpx.AsyncClient(timeout=30) as client:
            # -- voice zone -------------------------------------------------
            offset = 0
            seen: set[str] = set()
            while True:
                data = await _post(
                    client,
                    "/plpl/room/main/listByCat",
                    session,
                    params={"catId": 1, "limit": 50, "offset": offset},
                )
                if not _is_success(data):
                    break
                items = _get_data(data).get("list", [])
                if not items:
                    break
                for item in items:
                    room_id = str(item.get("unRoomId", ""))
                    if not room_id or room_id in seen:
                        continue
                    seen.add(room_id)
                    rooms.append(
                        Room(
                            id=room_id,
                            name=item.get("roomName", ""),
                            type="voice",
                            audience_count=item.get("audienceCount", 0),
                            raw=item,
                        )
                    )
                if len(items) < 50:
                    break
                offset += 50

            # -- video zone -------------------------------------------------
            seen_video: set[str] = set()
            for cat_id in VIDEO_CAT_IDS:
                offset = 0
                while True:
                    data = await _post(
                        client,
                        "/plpl/live/category/live",
                        session,
                        params={"categoryId": cat_id, "limit": 20, "offset": offset},
                    )
                    if not _is_success(data):
                        break
                    items = _get_data(data).get("list", [])
                    if not items:
                        break
                    for item in items:
                        live = item.get("live", {})
                        user_info = item.get("user", {})
                        lid = str(live.get("lid", ""))
                        if not lid or lid in seen_video:
                            continue
                        seen_video.add(lid)
                        name = user_info.get("name", "") or live.get("title", "")
                        rooms.append(
                            Room(
                                id=lid,
                                name=name,
                                type="video",
                                audience_count=live.get("audienceCount", 0),
                                raw=item,
                            )
                        )
                    if len(items) < 20:
                        break
                    offset += 20

        return rooms

    # ------------------------------------------------------------------
    # fetch_users
    # ------------------------------------------------------------------
    async def fetch_users(self, session: dict, room: Room) -> list[User]:
        """Fetch ranked (contribute) users from a single room.

        Voice rooms use unRoomId + /room/rank/list/contribute/rank.
        Video rooms use the anchor's uid (tid) + /gift/list/contribute/rank.
        """
        users: list[User] = []
        async with httpx.AsyncClient(timeout=30) as client:
            if room.type == "voice":
                users = await self._fetch_voice_users(client, session, room)
            else:
                users = await self._fetch_video_users(client, session, room)
        return users

    async def _fetch_voice_users(
        self, client: httpx.AsyncClient, session: dict, room: Room
    ) -> list[User]:
        users: list[User] = []
        offset = 0
        while True:
            data = await _post(
                client,
                "/room/rank/list/contribute/rank",
                session,
                params={
                    "unRoomId": room.id,
                    "period": "WEEKLY",
                    "offset": offset,
                    "limit": 50,
                },
            )
            if not _is_success(data):
                break
            items = _get_data(data).get("list", [])
            if not items:
                break
            for idx, item in enumerate(items):
                uid = str(item.get("uid", ""))
                if not uid:
                    continue
                users.append(
                    User(
                        app_uid=uid,
                        name=item.get("name", ""),
                        room_id=room.id,
                        room_type="voice",
                        rank=offset + idx + 1,
                        gender=item.get("gender"),
                        score=item.get("count"),
                        extra={"shortId": item.get("shortId", "")},
                        raw=item,
                    )
                )
            if len(items) < 50:
                break
            offset += 50
        return users

    async def _fetch_video_users(
        self, client: httpx.AsyncClient, session: dict, room: Room
    ) -> list[User]:
        users: list[User] = []
        # The anchor's uid is the tid for video room contribute rank
        anchor_uid = room.raw.get("user", {}).get("uid", "")
        if not anchor_uid:
            return users

        offset = 0
        while True:
            data = await _post(
                client,
                "/gift/list/contribute/rank",
                session,
                params={
                    "tid": str(anchor_uid),
                    "period": "WEEKLY",
                    "offset": offset,
                    "limit": 50,
                },
            )
            if not _is_success(data):
                break
            items = _get_data(data).get("list", [])
            if not items:
                break
            for idx, item in enumerate(items):
                uid = str(item.get("uid", ""))
                if not uid:
                    continue
                users.append(
                    User(
                        app_uid=uid,
                        name=item.get("name", ""),
                        room_id=room.id,
                        room_type="video",
                        rank=offset + idx + 1,
                        gender=item.get("gender"),
                        score=item.get("count"),
                        extra={"shortId": item.get("shortId", "")},
                        raw=item,
                    )
                )
            if len(items) < 50:
                break
            offset += 50
        return users

    # ------------------------------------------------------------------
    # send_message
    # ------------------------------------------------------------------
    async def send_message(self, session: dict, user: User, message: Message) -> SendResult:
        """Send a DM to a user via the 3‑step Popo private‑message flow.

        1.  /plpl/relation/get/user/in/chat  → user info
        2.  /plpl/pr/chat/preCheck           → msgChatId
        3.  /plpl/relation/in/chat/send      → send the message
        """
        tid = user.app_uid
        body_text = message.render()
        payload = json.dumps({"body": body_text, "seconds": 0}, ensure_ascii=False)

        t0 = time.perf_counter()
        steps = []
        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1 — get user info in chat context
            step1 = await _post(
                client,
                "/plpl/relation/get/user/in/chat",
                session,
                params={"tid": tid},
            )
            steps.append(("get_user_in_chat", step1.get("code")))
            if not _is_success(step1):
                cost = int((time.perf_counter() - t0) * 1000)
                return SendResult(
                    success=False,
                    error_code=step1.get("code", "F_UNKNOWN"),
                    error_msg=step1.get("message", "get user info failed"),
                    cost_ms=cost,
                    raw={"steps": steps},
                )

            # Step 2 — pre‑check (obtains server‑side msgChatId)
            step2 = await _post(
                client,
                "/plpl/pr/chat/preCheck",
                session,
                params={"tid": tid},
            )
            steps.append(("preCheck", step2.get("code")))
            if not _is_success(step2):
                cost = int((time.perf_counter() - t0) * 1000)
                return SendResult(
                    success=False,
                    error_code=step2.get("code", "F_UNKNOWN"),
                    error_msg=step2.get("message", "preCheck failed"),
                    cost_ms=cost,
                    raw={"steps": steps},
                )
            msg_chat_id = _get_data(step2).get("msgChatId", "")
            if not msg_chat_id:
                cost = int((time.perf_counter() - t0) * 1000)
                return SendResult(
                    success=False,
                    error_code="F_NO_MSGCHATID",
                    error_msg="preCheck returned no msgChatId",
                    cost_ms=cost,
                    raw={"steps": steps},
                )

            # Step 3 — send
            step3 = await _post(
                client,
                "/plpl/relation/in/chat/send",
                session,
                tid=tid,
                msgChatId=msg_chat_id,
                body=payload,
            )
            steps.append(("send", step3.get("code")))
            cost = int((time.perf_counter() - t0) * 1000)

            success = _is_success(step3)
            return SendResult(
                success=success,
                error_code="" if success else step3.get("code", "F_UNKNOWN"),
                error_msg="" if success else step3.get("message", ""),
                cost_ms=cost,
                raw={"steps": steps, "msgChatId": msg_chat_id},
            )

    # ------------------------------------------------------------------
    # check_health
    # ------------------------------------------------------------------
    async def check_health(self, session: dict) -> HealthStatus:
        """Check account validity.

        Uses `/plpl/main/list/hot/v3` as a canary.  If the API returns
        successfully but all live lists are empty the account is likely
        shadow‑banned.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                data = await _post(client, "/plpl/main/list/hot/v3", session)
            except httpx.HTTPError:
                return HealthStatus.WARNING

            if not _is_success(data):
                code = data.get("code", "")
                if "BAN" in str(code).upper():
                    return HealthStatus.BANNED
                return HealthStatus.WARNING

            payload = _get_data(data)
            # Aggregate every list field that could contain live items
            list_keys = [
                "topLiveList",
                "starLiveList",
                "liveList",
                "pkLiveList",
                "liveRecommendList",
            ]
            total_items = sum(
                len(payload.get(k, []) or []) for k in list_keys
            )
            if total_items == 0:
                # Silent shadow‑ban: S_OK but no data
                return HealthStatus.BANNED

            return HealthStatus.OK


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _random_meid() -> str:
    """Generate a 14‑character hex string for use as a device ID."""
    import random
    return "".join(random.choice("0123456789abcdef") for _ in range(14))
