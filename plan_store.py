from __future__ import annotations

import json
from typing import Tuple


def default_plan_text() -> str:
    return "俯卧撑 | 4组 | 力竭 | 休90\n下斜俯卧撑 | 3组 | 15次 | 休60"


async def prefs_get(prefs, key: str, default=None):
    try:
        return await prefs.get(key)
    except Exception:
        return default


async def prefs_set(prefs, key: str, value):
    try:
        await prefs.set(key, value)
    except Exception:
        pass


async def load_plans(prefs, storage_key: str) -> dict:
    raw = await prefs_get(prefs, storage_key)
    if not raw:
        return {}
    try:
        plans = json.loads(raw)
        return plans if isinstance(plans, dict) else {}
    except Exception:
        return {}


async def save_plans(prefs, storage_key: str, plans: dict):
    await prefs_set(prefs, storage_key, json.dumps(plans, ensure_ascii=False))


async def get_last_plan_id(prefs, key: str):
    return await prefs_get(prefs, key)


async def set_last_plan_id(prefs, key: str, plan_id: str):
    await prefs_set(prefs, key, plan_id)


async def init_plans_state(prefs, storage_key: str, last_plan_id_key: str) -> Tuple[dict, str, str]:
    plans = await load_plans(prefs, storage_key)
    last_plan_id = await get_last_plan_id(prefs, last_plan_id_key)

    if last_plan_id and last_plan_id in plans:
        initial_text = plans[last_plan_id].get("text", "") or ""
    elif plans:
        first_id = sorted(plans.keys())[0]
        initial_text = plans[first_id].get("text", "") or ""
        await set_last_plan_id(prefs, last_plan_id_key, first_id)
        last_plan_id = first_id
    else:
        plan_id = "default"
        plans[plan_id] = {"name": "示例计划", "text": default_plan_text()}
        await save_plans(prefs, storage_key, plans)
        await set_last_plan_id(prefs, last_plan_id_key, plan_id)
        last_plan_id = plan_id
        initial_text = plans[plan_id]["text"]

    return plans, last_plan_id, initial_text
