from typing import Any


REQUIRED_KEYS = ["title", "date", "main_points", "metrics", "keywords"]


def normalize_extracted(payload: Any) -> tuple[bool, dict, str]:
    if not isinstance(payload, dict):
        return False, {}, "payload必须是JSON对象"

    normalized = {}
    for key in REQUIRED_KEYS:
        normalized[key] = payload.get(key)

    if not normalized["title"]:
        return False, normalized, "缺少title"

    if not isinstance(normalized["main_points"], list):
        normalized["main_points"] = []

    if not isinstance(normalized["metrics"], dict):
        normalized["metrics"] = {}

    if not isinstance(normalized["keywords"], list):
        normalized["keywords"] = []

    if not normalized["date"]:
        normalized["date"] = "unknown"

    return True, normalized, ""
