"""Generic plugin driven by api_spec.json — no manual coding needed per APP.

Each APP is described by a single spec dict (loaded from JSON) that defines:
  - base_url, common_params, auth flow, endpoints, and status codes.

GenericPlugin reads the spec at construction time and implements all five
BasePlugin methods by following the declarative steps in the spec.
"""
from __future__ import annotations

import copy
import re
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

# Matches {token}, {uid}, {room.id}, {user.app_uid}, {message.body}
_PLACEHOLDER_RE = re.compile(r"\{(\w+(?:\.\w+)*)\}")


# ---------------------------------------------------------------------------
# module-level helpers
# ---------------------------------------------------------------------------


def _navigate(data: Any, path: str) -> Any:
    """Traverse a dotted path into a nested dict.  Returns None on missing keys.

    Examples
    --------
    _navigate({"data": {"list": [1,2]}}, "data.list")  → [1, 2]
    _navigate({"data": {"token": "abc"}}, "data.token") → "abc"
    """
    if not path:
        return data
    for key in path.split("."):
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


def _to_int(val: Any) -> int:
    """Safely convert any value to int. Returns 0 on failure."""
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# GenericPlugin
# ---------------------------------------------------------------------------


class GenericPlugin(BasePlugin):
    """Spec-driven plugin.  No APP-specific code needed — just load a spec dict.

    Usage::

        spec = json.load(open("api_spec.json"))
        plugin = GenericPlugin(spec)
        # plugin.app_name == spec["app"]
    """

    app_name: str  # set in __init__ from spec["app"]

    def __init__(self, spec: dict):
        self.spec = spec
        self.app_name = spec.get("app", "")
        self.base_url: str = spec.get("base_url", "").rstrip("/")
        self.common_params: dict = spec.get("common_params", {})
        self.status_codes: dict = spec.get("status_codes", {})
        self.endpoints: dict = spec.get("endpoints", {})

    # ======================================================================
    # Substitution engine
    # ======================================================================

    def _build_sub_map(self, session: dict, /, **extra: Any) -> dict[str, str]:
        """Build a flat ``{placeholder: string_value}`` map.

        Sources (in priority order — later keys shadow earlier ones):
        1. Every key in ``session`` (e.g. ``{token}``, ``{uid}``).
        2. For each **extra kwarg whose value is a dict**, both
           ``{prefix.key}`` and bare ``{key}`` are registered.
        3. For each **extra kwarg that is a dataclass**, only the
           prefixed form ``{prefix.field}`` is registered.
        """
        subs: dict[str, str] = {}

        # 1 — session keys
        for k, v in session.items():
            subs[k] = str(v) if v is not None else ""

        # 2 & 3 — extras
        for name, obj in extra.items():
            if obj is None:
                continue
            if isinstance(obj, dict):
                for k, v in obj.items():
                    s = str(v) if v is not None else ""
                    subs[f"{name}.{k}"] = s
                    # bare key for credential-like dicts so that
                    # {phone} works inside auth flow body templates
                    subs[k] = s
            else:
                # Dataclass or plain object — use __dataclass_fields__ if
                # present, otherwise fall back to vars().
                fields = getattr(obj, "__dataclass_fields__", None)
                if fields is None:
                    fields = vars(obj)
                for field_name in fields:
                    val = getattr(obj, field_name, "")
                    subs[f"{name}.{field_name}"] = (
                        str(val) if val is not None else ""
                    )
        return subs

    def _substitute(self, template: Any, session: dict, **extra: Any) -> Any:
        """Recursively replace ``{placeholder}`` in strings, dict keys/values,
        and list items."""
        subs = self._build_sub_map(session, **extra)
        return self._sub_recurse(template, subs)

    def _sub_recurse(self, template: Any, subs: dict[str, str]) -> Any:
        if isinstance(template, str):
            return _PLACEHOLDER_RE.sub(
                lambda m: subs.get(m.group(1), m.group(0)), template
            )
        if isinstance(template, dict):
            return {k: self._sub_recurse(v, subs) for k, v in template.items()}
        if isinstance(template, list):
            return [self._sub_recurse(v, subs) for v in template]
        return template

    # ======================================================================
    # HTTP helpers
    # ======================================================================

    async def _request_step(
        self,
        client: httpx.AsyncClient,
        step: dict,
        session: dict,
        **extra: Any,
    ) -> dict:
        """Execute a single API step — login-flow step, endpoint, or pre_step.

        Parameters
        ----------
        client:
            A shared ``httpx.AsyncClient``.
        step:
            A dict with keys ``method``, ``path``, and optionally
            ``params`` or ``body``.
        session:
            The plugin session dict (contains ``token``, ``uid``, …).
        extra:
            Additional substitution context (e.g. ``room=…``, ``user=…``,
            ``message=…``, ``credential=…``).
        """
        method = step.get("method", "POST").upper()
        path_template: str = step.get("path", "")
        path = self._substitute(path_template, session, **extra)

        headers = {
            "User-Agent": "okhttp/3.14.9",
            "Content-Type": "application/json; charset=utf-8",
        }

        # Assemble the request body / query string --------------------------
        body: dict[str, Any] = {}

        # 1.  Common body params defined at the top level of the spec
        if self.common_params.get("body"):
            body.update(
                self._substitute(self.common_params["body"], session, **extra)
            )

        # 2.  Step-level params & body (merged together for POST-like calls)
        for param_key in ("params", "body"):
            if step.get(param_key):
                body.update(
                    self._substitute(step[param_key], session, **extra)
                )

        url = f"{self.base_url}{path}"

        if method in ("POST", "PUT", "PATCH"):
            resp = await client.request(method, url, json=body, headers=headers)
        else:
            resp = await client.request(method, url, params=body, headers=headers)

        resp.raise_for_status()
        return resp.json()

    def _check_success(self, data: Any) -> bool:
        """Return True if *data* matches ``status_codes.success``.

        Tries fields ``code``, ``status``, ``result`` in that order.
        If none of those fields exist we assume success.
        """
        expected = self.status_codes.get("success", "")
        if not expected:
            return True
        if not isinstance(data, dict):
            return True
        for field in ("code", "status", "result"):
            if field in data:
                return str(data[field]) == str(expected)
        return True

    # ======================================================================
    # BasePlugin — authenticate
    # ======================================================================

    async def authenticate(self, credential: dict) -> AuthResult:
        """Run the login_flow steps and extract token + uid."""
        login_flow = self.spec.get("auth", {}).get("login_flow", [])
        if not login_flow:
            return AuthResult(
                success=False, error="No login_flow defined in spec"
            )

        phone = credential.get("phone", "")
        if not phone:
            return AuthResult(
                success=False, error="Missing 'phone' in credential"
            )

        async with httpx.AsyncClient(timeout=30) as client:
            last_data: dict = {}
            for i, step in enumerate(login_flow):
                try:
                    last_data = await self._request_step(
                        client, step, {}, credential=credential
                    )
                except httpx.HTTPError as exc:
                    return AuthResult(
                        success=False,
                        error=f"Auth step {i} failed (HTTP): {exc}",
                    )
                except Exception as exc:
                    return AuthResult(
                        success=False,
                        error=f"Auth step {i} failed: {exc}",
                    )

            # Extract token & uid from the **last** step's response ---------
            final_step = login_flow[-1]
            token_path: str = final_step.get("extract_token_from", "")
            uid_path: str = final_step.get("extract_uid_from", "")

            token = str(_navigate(last_data, token_path) or "") if token_path else ""
            uid = str(_navigate(last_data, uid_path) or "") if uid_path else ""

            if not token:
                return AuthResult(
                    success=False,
                    error="No token extracted from auth response",
                )

            return AuthResult(
                success=True,
                session={
                    "phone": phone,
                    "smsCode": credential.get("smsCode", ""),
                    "token": token,
                    "uid": uid,
                    "raw": last_data,
                },
            )

    # ======================================================================
    # BasePlugin — fetch_rooms
    # ======================================================================

    async def fetch_rooms(self, session: dict, filters: dict) -> list[Room]:
        """Paginate through the room_list endpoint and build Room objects."""
        ep_template = self.endpoints.get("room_list", {})
        if not ep_template:
            return []

        # Deep-copy so we can mutate pagination params safely
        ep = copy.deepcopy(ep_template)

        pagination: str = ep.get("pagination", "")
        pagination_param: str = ep.get("pagination_param", "page")
        limit: int = _to_int(
            ep.get("params", {}).get("size")
            or ep.get("params", {}).get("limit")
        ) or 50

        response_list_path: str = ep.get("response_list_path", "")

        room_id_field: str = ep.get("room_id_field", "roomId")
        room_name_field: str = ep.get("room_name_field", "roomName")
        room_audience_field: str = ep.get("room_audience_field", "onlineCount")
        room_type_default: str = ep.get("room_type_default", "voice")
        room_type_field: str = ep.get("room_type_field", "")
        room_type_field_mapping: dict = ep.get("room_type_field_mapping", {}) or {}

        rooms: list[Room] = []
        offset = 0
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                # Inject pagination offset into the request params ----------
                if pagination == "offset_limit":
                    ep["params"][pagination_param] = offset

                try:
                    data = await self._request_step(client, ep, session)
                except httpx.HTTPError:
                    break

                items = (
                    _navigate(data, response_list_path)
                    if response_list_path
                    else data
                )
                # Some APIs wrap the list in another dict layer
                if isinstance(items, dict):
                    items = items.get("list", items.get("items", []))
                if not isinstance(items, list) or not items:
                    break

                for item in items:
                    room_id = str(item.get(room_id_field, ""))
                    if not room_id or room_id in seen:
                        continue
                    seen.add(room_id)

                    # Resolve room type -------------------------------------
                    if room_type_field:
                        raw_type = str(item.get(room_type_field, ""))
                        room_type = room_type_field_mapping.get(
                            raw_type, room_type_default
                        )
                    else:
                        room_type = room_type_default

                    rooms.append(
                        Room(
                            id=room_id,
                            name=item.get(room_name_field, "") or "",
                            type=room_type,
                            audience_count=_to_int(
                                item.get(room_audience_field, 0)
                            ),
                            raw=item,
                        )
                    )

                if len(items) < limit:
                    break
                offset += limit

        return rooms

    # ======================================================================
    # BasePlugin — fetch_users
    # ======================================================================

    async def fetch_users(self, session: dict, room: Room) -> list[User]:
        """Paginate through the room_users endpoint and build User objects."""
        ep_template = self.endpoints.get("room_users", {})
        if not ep_template:
            return []

        ep = copy.deepcopy(ep_template)

        pagination: str = ep.get("pagination", "")
        pagination_param: str = ep.get("pagination_param", "page")
        limit: int = _to_int(
            ep.get("params", {}).get("size")
            or ep.get("params", {}).get("limit")
        ) or 50

        response_list_path: str = ep.get("response_list_path", "")

        uid_field: str = ep.get("user_uid_field", "userId")
        name_field: str = ep.get("user_name_field", "nickname")
        gender_field: str = ep.get("user_gender_field", "")
        score_field: str = ep.get("user_score_field", "")

        users: list[User] = []
        offset = 0

        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                if pagination == "offset_limit":
                    ep["params"][pagination_param] = offset

                try:
                    data = await self._request_step(
                        client, ep, session, room=room
                    )
                except httpx.HTTPError:
                    break

                items = (
                    _navigate(data, response_list_path)
                    if response_list_path
                    else data
                )
                if isinstance(items, dict):
                    items = items.get("list", items.get("items", []))
                if not isinstance(items, list) or not items:
                    break

                for idx, item in enumerate(items):
                    app_uid = str(item.get(uid_field, ""))
                    if not app_uid:
                        continue

                    # Resolve gender ----------------------------------------
                    gender: str | None = None
                    if gender_field:
                        raw_gender = str(item.get(gender_field, "")).lower()
                        if raw_gender in ("male", "m", "男", "1"):
                            gender = "male"
                        elif raw_gender in ("female", "f", "女", "2", "0"):
                            gender = "female"

                    # Resolve score -----------------------------------------
                    score = None
                    if score_field:
                        score = _to_int(item.get(score_field))

                    users.append(
                        User(
                            app_uid=app_uid,
                            name=item.get(name_field, "") or "",
                            room_id=room.id,
                            room_type=room.type,
                            rank=offset + idx + 1,
                            gender=gender,
                            score=score,
                            raw=item,
                        )
                    )

                if len(items) < limit:
                    break
                offset += limit

        return users

    # ======================================================================
    # BasePlugin — send_message
    # ======================================================================

    async def send_message(
        self, session: dict, user: User, message: Message
    ) -> SendResult:
        """Send a DM.  Runs pre_steps first, then the actual send call."""
        ep = self.endpoints.get("send_message", {})
        if not ep:
            return SendResult(
                success=False,
                error_code="NO_ENDPOINT",
                error_msg="send_message not defined in spec",
            )

        t0 = time.perf_counter()
        steps_log: list[tuple[str, Any]] = []
        # Accumulate values extracted from pre_steps so downstream
        # substitution can reference them by bare name (e.g. {msgChatId})
        extracted: dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=30) as client:
            # -- pre_steps --------------------------------------------------
            for pre_step in ep.get("pre_steps", []):
                # Merge extracted values into the session for substitution
                merged_session = {**session, **extracted}
                try:
                    pre_data = await self._request_step(
                        client,
                        pre_step,
                        merged_session,
                        user=user,
                        message=message,
                    )
                except httpx.HTTPError as exc:
                    cost = int((time.perf_counter() - t0) * 1000)
                    return SendResult(
                        success=False,
                        error_code="HTTP_ERROR",
                        error_msg=str(exc),
                        cost_ms=cost,
                        raw={"steps": steps_log},
                    )
                except Exception as exc:
                    cost = int((time.perf_counter() - t0) * 1000)
                    return SendResult(
                        success=False,
                        error_code="UNEXPECTED",
                        error_msg=str(exc),
                        cost_ms=cost,
                        raw={"steps": steps_log},
                    )

                # Extract declared values into the flat context -------------
                for var_name, json_path in pre_step.get("extract", {}).items():
                    val = _navigate(pre_data, json_path)
                    extracted[var_name] = val
                    steps_log.append(
                        (f"extract:{var_name}", str(val)[:120])
                    )

            # -- final send -------------------------------------------------
            merged_session = {**session, **extracted}
            try:
                data = await self._request_step(
                    client,
                    ep,
                    merged_session,
                    user=user,
                    message=message,
                )
            except httpx.HTTPError as exc:
                cost = int((time.perf_counter() - t0) * 1000)
                return SendResult(
                    success=False,
                    error_code="HTTP_ERROR",
                    error_msg=str(exc),
                    cost_ms=cost,
                    raw={"steps": steps_log},
                )
            except Exception as exc:
                cost = int((time.perf_counter() - t0) * 1000)
                return SendResult(
                    success=False,
                    error_code="UNEXPECTED",
                    error_msg=str(exc),
                    cost_ms=cost,
                    raw={"steps": steps_log},
                )

            cost = int((time.perf_counter() - t0) * 1000)

            # -- success check ----------------------------------------------
            success_check: dict = ep.get("success_check", {})
            if success_check:
                field: str = success_check.get("field", "code")
                expected = str(success_check.get("value", ""))
                actual = _navigate(data, field)
                success = str(actual) == expected if actual is not None else False
            else:
                success = self._check_success(data)

            return SendResult(
                success=success,
                error_code="" if success else str(data.get("code", "F_UNKNOWN")),
                error_msg="" if success else str(data.get("message", "")),
                cost_ms=cost,
                raw={"steps": steps_log, "response": data},
            )

    # ======================================================================
    # BasePlugin — check_health
    # ======================================================================

    async def check_health(self, session: dict) -> HealthStatus:
        """Ping the health_check endpoint (or room_list with size=1 as
        fallback) to determine whether the account is still valid."""
        health_ep = self.endpoints.get("health_check", {})

        if not health_ep:
            # Fall back to room_list with minimal page size -----------------
            room_ep = self.endpoints.get("room_list", {})
            if not room_ep:
                return HealthStatus.WARNING
            health_ep = copy.deepcopy(room_ep)
            params = health_ep.get("params", {})
            for size_key in ("size", "limit"):
                if size_key in params:
                    params[size_key] = 1
                    break

        response_list_path: str = health_ep.get("response_list_path", "")

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                data = await self._request_step(client, health_ep, session)
            except (httpx.HTTPError, Exception):
                return HealthStatus.WARNING

            if not self._check_success(data):
                # Check for explicit ban codes
                for field in ("code", "status", "message", "msg"):
                    val = str(data.get(field, ""))
                    if "BAN" in val.upper() or "BLOCK" in val.upper():
                        return HealthStatus.BANNED
                return HealthStatus.WARNING

            # Even on success, an empty response may indicate shadow-ban ----
            if response_list_path:
                items = _navigate(data, response_list_path)
                if isinstance(items, dict):
                    items = items.get("list", items.get("items"))
                if items is None or (
                    isinstance(items, (list, dict)) and len(items) == 0
                ):
                    return HealthStatus.BANNED

            return HealthStatus.OK
