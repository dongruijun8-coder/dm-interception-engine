"""Pipeline orchestrator — runs the 6-step flow for a task."""
import asyncio
import logging
from engine.models import TaskStatus, HealthStatus, Message, User
from engine.plugin_base import BasePlugin
from engine.filters import apply_filters
from engine.templates import pick_random
from engine import db

logger = logging.getLogger(__name__)


async def run_pipeline(plugin: BasePlugin, task_id: int, task_config: dict):
    """Execute the full pipeline for a task. Updates DB as it progresses."""

    task = await db.get_task(task_id)
    account = await db.get_account(task["account_id"])
    app_name = plugin.app_name
    session = account.get("session_data", {})
    filter_config = task_config.get("filters", {})

    try:
        # ── Step 1: Auth ──
        await db.update_task_status(task_id, TaskStatus.AUTHENTICATING)
        credential = {"phone": account.get("phone", ""), "token": account.get("token", "")}
        auth_result = await plugin.authenticate(credential)
        if not auth_result.success:
            await db.update_task_status(task_id, TaskStatus.FAILED)
            logger.error(f"[{app_name}] Auth failed: {auth_result.error}")
            return
        session = auth_result.session
        await db.update_account_token(account["id"], account.get("token", ""), session)

        # ── Step 2: Health check ──
        health = await plugin.check_health(session)
        await db.update_account_health(account["id"], health.value)
        if health != HealthStatus.OK:
            logger.warning(f"[{app_name}] Health check: {health.value}, continuing anyway")

        # ── Step 3: Fetch rooms ──
        await db.update_task_status(task_id, TaskStatus.FETCHING)
        rooms = await plugin.fetch_rooms(session, filter_config)
        logger.info(f"[{app_name}] Fetched {len(rooms)} rooms")
        await db.update_task_stat(task_id, rooms_fetched=len(rooms))

        # ── Step 4: Fetch users from each room ──
        all_users = []
        for room in rooms:
            try:
                users = await plugin.fetch_users(session, room)
                all_users.extend(users)
            except Exception as e:
                logger.warning(f"[{app_name}] Failed to fetch users from room {room.id}: {e}")
                continue

        logger.info(f"[{app_name}] Fetched {len(all_users)} users total")

        # Deduplicate by app_uid within this task
        seen = set()
        deduped = []
        for u in all_users:
            if u.app_uid not in seen:
                seen.add(u.app_uid)
                deduped.append(u)
        logger.info(f"[{app_name}] After dedup: {len(deduped)} users")
        await db.update_task_stat(task_id, users_fetched=len(all_users), users_deduped=len(deduped))

        # ── Step 5: Apply filters ──
        sent_uids = set()
        if filter_config.get("skip_sent"):
            sent_uids = await db.get_sent_app_uids(app_name)
        filtered = apply_filters(deduped, filter_config, sent_uids)
        logger.info(f"[{app_name}] After filters: {len(filtered)} users")

        # Insert filtered users into DB
        for u in filtered:
            await db.insert_user(task_id, app_name, u)

        # ── Step 6: Send messages ──
        await db.update_task_status(task_id, TaskStatus.SENDING)
        msg_sent = 0
        msg_success = 0
        msg_failed = 0

        db_users = await db.get_task_users(task_id)
        for db_user in db_users:
            tpl = pick_random(app_name, db_user["name"])
            if not tpl:
                logger.warning(f"[{app_name}] No templates configured, skipping send phase")
                break

            message = Message(body=tpl, template_vars={"name": db_user["name"] or ""})

            # Reconstruct User from DB row
            user = User(
                app_uid=db_user["app_uid"],
                name=db_user["name"] or "",
                room_id=db_user["room_id"] or "",
                room_type=db_user["room_type"] or "voice",
                rank=db_user["rank"] or 0,
                gender=db_user.get("gender"),
                score=db_user.get("score"),
                extra={},
                raw={}
            )

            result = await plugin.send_message(session, user, message)
            msg_sent += 1
            if result.success:
                msg_success += 1
            else:
                msg_failed += 1
                logger.info(f"[{app_name}] Skip user {user.app_uid}: {result.error_code}")

            await db.log_send(db_user["id"], task_id, message.body, result)
            await db.update_task_stat(task_id, msg_sent=msg_sent, msg_success=msg_success, msg_failed=msg_failed)

        await db.update_task_status(task_id, TaskStatus.DONE)
        logger.info(f"[{app_name}] Pipeline done: sent={msg_sent}, ok={msg_success}, fail={msg_failed}")

    except Exception as e:
        logger.exception(f"[{app_name}] Pipeline failed: {e}")
        await db.update_task_status(task_id, TaskStatus.FAILED)
