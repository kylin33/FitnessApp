from __future__ import annotations

from typing import Callable


def parse_plan(text: str, debug: Callable[[str], None] | None = None) -> list[dict]:
    """Parse workout text into task list.

    Supported format:
    # title
    [phase]
    jump | 1分钟
    push-up | 4组 | 力竭 | 休90
    """
    plan: list[dict] = []
    lines = (text or "").strip().split("\n")
    current_phase = "训练"

    def _dbg(msg: str) -> None:
        if debug:
            debug(msg)

    def _extract_int(raw: str, default: int = 0) -> int:
        digits = "".join(ch for ch in (raw or "") if ch.isdigit())
        return int(digits) if digits else default

    def _parse_duration_seconds(raw: str) -> int:
        t = (raw or "").strip().lower().replace(" ", "")
        if not t:
            return 0
        if t in {"无", "none", "n/a", "na", "-"}:
            return 0
        if "无" in t and not any(ch.isdigit() for ch in t):
            return 0

        if "分" in t:
            min_part, sec_part = t.split("分", 1)
            mins = _extract_int(min_part, 0)
            secs = _extract_int(sec_part, 0) if ("秒" in sec_part or sec_part.endswith("s")) else 0
            return mins * 60 + secs

        if "秒" in t or t.endswith("s"):
            return _extract_int(t, 0)

        return _extract_int(t, 0)

    for line in lines:
        raw = (line or "").strip()
        if not raw:
            continue
        if raw.startswith("#"):
            _dbg(f"parse_plan title={raw.lstrip('#').strip()}")
            continue
        if raw.startswith("[") and raw.endswith("]"):
            current_phase = raw[1:-1].strip() or "训练"
            _dbg(f"parse_plan phase={current_phase}")
            continue
        if "|" not in raw:
            continue

        parts = [p.strip() for p in raw.split("|")]

        if len(parts) == 2:
            action_name = parts[0]
            target_raw = parts[1]
            secs = _parse_duration_seconds(target_raw)
            target = {"kind": "time", "seconds": secs} if secs > 0 else {"kind": "reps", "text": target_raw}
            plan.append(
                {
                    "name": action_name,
                    "set_info": f"[{current_phase}] 第 1 组 / 共 1 组",
                    "target": target,
                    "rest": 0,
                }
            )
            continue

        if len(parts) >= 4:
            action_name = parts[0]
            sets = _extract_int(parts[1], 0)
            if sets <= 0:
                continue
            target_raw = parts[2]
            rest_sec = _parse_duration_seconds(parts[3])

            def _parse_target(t: str) -> dict:
                tl = (t or "").strip().lower().replace(" ", "")
                if "秒" in tl or "分" in tl or tl.endswith("s"):
                    return {"kind": "time", "seconds": _parse_duration_seconds(t)}
                return {"kind": "reps", "text": t}

            for s in range(sets):
                plan.append(
                    {
                        "name": action_name,
                        "set_info": f"[{current_phase}] 第 {s + 1} 组 / 共 {sets} 组",
                        "target": _parse_target(target_raw),
                        "rest": rest_sec,
                    }
                )

    return plan
