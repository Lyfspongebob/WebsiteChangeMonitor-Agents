from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.db import get_change_counts_last_days, get_keyword_like_counts, insert_analytics_result


def _get_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.deepseek_model,
        api_key=s.deepseek_api_key,
        base_url=s.deepseek_base_url,
        temperature=0.2,
    )


def analyze_source(source_id: int) -> tuple[int, dict, str]:
    changes = get_change_counts_last_days(source_id, days=7)
    top_items = get_keyword_like_counts(source_id, days=30)

    total_changes = sum(int(x["c"]) for x in changes) if changes else 0
    metrics = {
        "changes_last_7_days": changes,
        "top_records_last_30_days": top_items,
        "total_changes": total_changes,
    }

    try:
        llm = _get_llm()
        prompt = f"""
你是数据分析助手。根据以下指标写3条简短洞察，中文输出。
指标：{metrics}
"""
        insight = llm.invoke(prompt).content
    except Exception:
        insight = f"最近7天共检测到{total_changes}次变化。"

    now = datetime.now()
    analytics_id = insert_analytics_result(
        source_id=source_id,
        period_start=now - timedelta(days=7),
        period_end=now,
        metrics_json=metrics,
        insight_text=insight,
    )
    return analytics_id, metrics, insight
