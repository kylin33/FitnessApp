from __future__ import annotations


def extract_plan_title(text: str) -> str:
    for line in (text or "").splitlines():
        raw = (line or "").strip()
        if raw.startswith("#"):
            t = raw.lstrip("#").strip()
            if t:
                return t
    return ""


def infer_plan_name(text: str) -> str:
    title = extract_plan_title(text)
    if title:
        return title
    first_line = (text or "").strip().splitlines()[0].strip() if (text or "").strip() else "训练计划"
    return first_line.split("|")[0].strip() or "训练计划"
