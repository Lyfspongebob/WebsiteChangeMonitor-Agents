import difflib
import hashlib


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def compute_diff_ratio(old_text: str, new_text: str) -> float:
    if not old_text and not new_text:
        return 0.0
    return 1.0 - difflib.SequenceMatcher(None, old_text, new_text).ratio()


def summarize_diff(old_text: str, new_text: str, max_lines: int = 8) -> str:
    old_lines = old_text.splitlines()[:300]
    new_lines = new_text.splitlines()[:300]
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    if not diff:
        return "无明显文本差异"
    return "\n".join(diff[:max_lines])
