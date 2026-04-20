from app.db import (
    create_change_event,
    get_recent_extraction_failures,
    get_latest_snapshot,
    get_snapshot_by_id,
    save_prompt_version,
    update_change_event_status,
    insert_snapshot,
)
from app.services.analyzer import analyze_source
from app.services.differ import compute_diff_ratio, compute_hash, summarize_diff
from app.services.extractor import get_llm, llm_extract
from app.services.fetcher import fetch_page, save_html_snapshot
from app.services.integrator import integrate_extracted
from app.services.reporter import build_report
from app.services.visualizer import build_charts
from app.utils.logger import get_logger

logger = get_logger("nodes")


def watch_node(state: dict) -> dict:
    source_id = state["source_id"]
    url = state["url"]
    css_selector = state.get("css_selector")

    latest = get_latest_snapshot(source_id)
    old_snapshot_id = latest["id"] if latest else None

    html, text = fetch_page(url, css_selector)
    content_hash = compute_hash(text)
    html_path = save_html_snapshot(source_id, html)
    snapshot_id = insert_snapshot(source_id, content_hash, text, html_path)

    logger.info(f"source={source_id} 抓取完成 snapshot_id={snapshot_id}")
    return {
        "raw_html": html,
        "raw_text": text,
        "content_hash": content_hash,
        "snapshot_id": snapshot_id,
        "old_snapshot_id": old_snapshot_id,
    }


def diff_node(state: dict) -> dict:
    source_id = state["source_id"]
    new_text = state.get("raw_text", "")
    old_snapshot_id = state.get("old_snapshot_id")

    if not old_snapshot_id:
        ceid = create_change_event(source_id, None, state["snapshot_id"], 1.0, "首次快照，视作变更", "detected")
        return {
            "is_changed": True,
            "diff_ratio": 1.0,
            "diff_summary": "首次快照，视作变更",
            "change_event_id": ceid,
        }

    old_snapshot = get_snapshot_by_id(old_snapshot_id)
    old_text = old_snapshot["raw_text"] if old_snapshot else ""

    ratio = compute_diff_ratio(old_text, new_text)
    changed = ratio >= 0.01 or (old_snapshot and old_snapshot.get("content_hash") != state.get("content_hash"))

    if not changed:
        return {
            "is_changed": False,
            "diff_ratio": ratio,
            "diff_summary": "未检测到显著变化",
        }

    summary = summarize_diff(old_text, new_text)
    ceid = create_change_event(
        source_id=source_id,
        old_snapshot_id=old_snapshot_id,
        new_snapshot_id=state["snapshot_id"],
        diff_ratio=ratio,
        diff_summary=summary,
        status="detected",
    )
    logger.info(f"source={source_id} 检测到变更 event_id={ceid}")
    return {"is_changed": True, "diff_ratio": ratio, "diff_summary": summary, "change_event_id": ceid}


def extract_node(state: dict) -> dict:
    if not state.get("is_changed"):
        return {}

    ok, data, err = llm_extract(state.get("raw_text", ""))
    event_id = state.get("change_event_id")
    if not ok:
        if event_id:
            update_change_event_status(event_id, "extract_invalid")
        return {"errors": [f"抽取失败: {err}"]}

    if event_id:
        update_change_event_status(event_id, "extracted")
    return {"extracted_data": data}


def integrate_node(state: dict) -> dict:
    if not state.get("is_changed"):
        return {}
    event_id = state.get("change_event_id")
    data = state.get("extracted_data")
    if not event_id or not data:
        if event_id:
            update_change_event_status(event_id, "extract_failed")
        return {"errors": ["缺少结构化数据，未融合"]}

    record_key = integrate_extracted(event_id, data, extractor_version="v1")
    update_change_event_status(event_id, "integrated")
    return {"record_key": record_key}


def analyze_node(state: dict) -> dict:
    if not state.get("is_changed"):
        return {}
    analytics_id, metrics, insight = analyze_source(state["source_id"])
    return {"analytics_id": analytics_id, "metrics": metrics, "insight": insight}


def visualize_node(state: dict) -> dict:
    if not state.get("is_changed"):
        return {}
    metrics = state.get("metrics", {})
    analytics_id = state.get("analytics_id")
    if not analytics_id:
        return {"errors": ["缺少analytics_id，跳过可视化"]}
    chart_paths = build_charts(state["source_id"], analytics_id, metrics)
    return {"chart_paths": chart_paths}


def report_node(state: dict) -> dict:
    if not state.get("is_changed"):
        return {}
    md_path, ppt_path = build_report(
        source_id=state["source_id"],
        source_name=state.get("source_name", f"source_{state['source_id']}"),
        insight=state.get("insight", "无"),
        chart_paths=state.get("chart_paths", []),
    )
    if state.get("change_event_id"):
        update_change_event_status(state["change_event_id"], "reported")
    return {"report_md_path": md_path, "ppt_path": ppt_path}


def reflect_node(state: dict) -> dict:
    failures = get_recent_extraction_failures(limit_n=5)
    errors = state.get("errors", [])
    if not failures and not errors:
        save_prompt_version("extractor", "当前prompt稳定，无需调整", score=1.0, is_active=1)
        return {}

    try:
        llm = get_llm()
        prompt = f"""
你是提示词优化助手。请根据抽取失败案例，给出一段更鲁棒的抽取提示词。
失败案例：{failures}
当前错误：{errors}
仅输出改进后的提示词文本。
"""
        new_prompt = llm.invoke(prompt).content[:4000]
        save_prompt_version("extractor", new_prompt, score=0.7, is_active=1)
    except Exception as e:
        save_prompt_version("extractor", f"反思节点失败: {e}", score=0.1, is_active=0)
    return {}
