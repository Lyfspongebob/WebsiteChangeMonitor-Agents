import json
import re

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.utils.schema_validator import normalize_extracted


def get_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.deepseek_model,
        api_key=s.deepseek_api_key,
        base_url=s.deepseek_base_url,
        temperature=0.2,
    )


def _extract_json_from_text(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("LLM返回中未找到JSON对象")
    return json.loads(match.group(0))


def fallback_extract(raw_text: str) -> dict:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    title = lines[0][:80] if lines else "未提取到标题"
    keywords = []
    for w in ["发布", "公告", "增长", "下降", "价格", "排名"]:
        if w in raw_text:
            keywords.append(w)
    return {
        "title": title,
        "date": "unknown",
        "main_points": lines[:5],
        "metrics": {},
        "keywords": keywords,
    }


def llm_extract(raw_text: str) -> tuple[bool, dict, str]:
    llm = get_llm()
    prompt = f"""
你是数据抽取助手。请从以下网页文本中提取关键信息，输出严格JSON，不要解释。

JSON结构：
{{
  "title": "字符串",
  "date": "日期或unknown",
  "main_points": ["要点1", "要点2"],
  "metrics": {{"字段名": 数值或字符串}},
  "keywords": ["关键词1", "关键词2"]
}}

网页文本：
{raw_text[:7000]}
"""
    try:
        res = llm.invoke(prompt)
        payload = _extract_json_from_text(res.content)
        ok, normalized, err = normalize_extracted(payload)
        return ok, normalized, err
    except Exception as e:
        fb = fallback_extract(raw_text)
        ok, normalized, err = normalize_extracted(fb)
        return ok, normalized, f"LLM抽取失败，已回退规则抽取: {e}; {err}"
