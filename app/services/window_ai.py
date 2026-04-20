import json
import os
import re
import subprocess
import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.config import get_settings
from app.db import get_window_change_events, get_window_source_change_stats
from app.services.extractor import get_llm
from app.utils.logger import get_logger

logger = get_logger("window_ai")


def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", s)


def _window_tag(start_dt: datetime, end_dt: datetime) -> str:
    return f"{start_dt.strftime('%Y%m%d_%H%M%S')}_{end_dt.strftime('%Y%m%d_%H%M%S')}"


def _extract_python_code(text: str) -> str:
    m = re.search(r"```python\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"```\s*([\s\S]*?)```", text)
    if m2:
        return m2.group(1).strip()
    return text.strip()


def _write_window_data_file(analysis_dir: str, window_tag: str, payload: dict) -> str:
    txt_path = os.path.join(analysis_dir, f"window_{window_tag}_data.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("# 40分钟窗口统计原始数据\n\n")
        f.write(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return txt_path


def _fallback_local_charts(charts_dir: str, window_tag: str, source_stats: list[dict], events: list[dict]) -> list[str]:
    chart_paths: list[str] = []

    names = [str(x.get("source_name", f"source_{x.get('source_id', 'unknown')}"))[:20] for x in source_stats]
    counts = [int(x.get("change_count", 0)) for x in source_stats]
    if names:
        fig1 = plt.figure(figsize=(9, 4.5))
        plt.bar(names, counts)
        plt.title("窗口期各网站变更次数")
        plt.xlabel("网站")
        plt.ylabel("次数")
        plt.xticks(rotation=25)
        plt.tight_layout()
        p1 = os.path.join(charts_dir, f"window_{window_tag}_by_source.png")
        fig1.savefig(p1)
        plt.close(fig1)
        chart_paths.append(p1)

    bins = [0, 0, 0, 0, 0]  # <0.01, [0.01,0.05), [0.05,0.1), [0.1,0.3), >=0.3
    for e in events:
        v = float(e.get("diff_ratio") or 0)
        if v < 0.01:
            bins[0] += 1
        elif v < 0.05:
            bins[1] += 1
        elif v < 0.1:
            bins[2] += 1
        elif v < 0.3:
            bins[3] += 1
        else:
            bins[4] += 1

    labels = ["<0.01", "0.01-0.05", "0.05-0.1", "0.1-0.3", ">=0.3"]
    fig2 = plt.figure(figsize=(8.5, 4.5))
    plt.bar(labels, bins)
    plt.title("窗口期 diff_ratio 分布")
    plt.xlabel("区间")
    plt.ylabel("事件数")
    plt.tight_layout()
    p2 = os.path.join(charts_dir, f"window_{window_tag}_diff_ratio_dist.png")
    fig2.savefig(p2)
    plt.close(fig2)
    chart_paths.append(p2)

    return chart_paths


def _generate_charts_by_llm(
    analysis_dir: str,
    charts_dir: str,
    window_tag: str,
    source_stats: list[dict],
    events: list[dict],
) -> tuple[list[str], str | None]:
    payload = {
        "source_stats": source_stats,
        "events": events,
    }
    data_path = os.path.join(analysis_dir, f"window_{window_tag}_viz_input.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    code_path = os.path.join(analysis_dir, f"window_{window_tag}_viz.py")
    index_path = os.path.join(analysis_dir, f"window_{window_tag}_charts.json")

    prompt = f"""
你是 Python 可视化工程师。请基于给定 JSON 数据，生成可直接运行的 Python 代码。

要求：
1) 仅输出一个 ```python 代码块，不要解释。
2) 代码使用 matplotlib（可选 pandas）读取这个 JSON：r"{data_path}"。
3) 至少生成2张图：
   - 各 source 的 change_count 柱状图
   - diff_ratio 分布图（直方图或分箱柱状图）
4) 图片输出到目录：r"{charts_dir}"，文件名前缀："window_{window_tag}_ai_"。
5) 代码最后将生成的图片绝对路径列表写入 JSON 文件：r"{index_path}"，格式为字符串数组。
6) 请确保代码可在 Windows 下直接运行。
"""

    llm = get_llm()
    content = llm.invoke(prompt).content
    code = _extract_python_code(content)
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        subprocess.run([sys.executable, code_path], check=True, capture_output=True, text=True)
    except Exception as e:
        logger.exception(f"LLM图表代码执行失败，将回退本地图表: {e}")
        return [], code_path

    if not os.path.exists(index_path):
        return [], code_path

    with open(index_path, "r", encoding="utf-8") as f:
        chart_paths = json.load(f)
    if not isinstance(chart_paths, list):
        chart_paths = []
    chart_paths = [str(p) for p in chart_paths if isinstance(p, str) and os.path.exists(p)]
    return chart_paths, code_path


def _generate_markdown_by_llm(
    reports_dir: str,
    window_tag: str,
    start_dt: datetime,
    end_dt: datetime,
    source_stats: list[dict],
    events: list[dict],
    chart_paths: list[str],
) -> str:
    md_path = os.path.join(reports_dir, f"window_{window_tag}_ai_report.md")
    payload = {
        "window": {
            "start": start_dt.isoformat(sep=" ", timespec="seconds"),
            "end": end_dt.isoformat(sep=" ", timespec="seconds"),
            "minutes": int((end_dt - start_dt).total_seconds() // 60),
        },
        "source_stats": source_stats,
        "events_sample": events[:50],
        "chart_paths": chart_paths,
    }
    llm = get_llm()
    prompt = f"""
你是数据分析报告助手。请根据以下JSON数据生成一份中文Markdown报告。

要求：
1) 标题为“40分钟网站变更分析报告”。
2) 包含：执行窗口、总体结论、各网站对比、波动分析、异常点、建议。
3) 在“图表”章节引用以下图片路径（原样输出为列表）：{chart_paths}
4) 输出必须是纯Markdown，不要代码块。

数据：
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}
"""
    try:
        md = llm.invoke(prompt).content.strip()
    except Exception as e:
        logger.exception(f"LLM报告生成失败，使用模板回退: {e}")
        md = "\n".join(
            [
                "# 40分钟网站变更分析报告",
                "",
                f"- 窗口开始：{start_dt.isoformat(sep=' ', timespec='seconds')}",
                f"- 窗口结束：{end_dt.isoformat(sep=' ', timespec='seconds')}",
                f"- 监控网站数：{len(source_stats)}",
                f"- 变更事件数：{len(events)}",
                "",
                "## 各网站变更统计",
                json.dumps(source_stats, ensure_ascii=False, indent=2, default=str),
                "",
                "## 图表",
                *[f"- {p}" for p in chart_paths],
            ]
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    return md_path


def run_window_ai_pipeline(start_dt: datetime, end_dt: datetime) -> dict:
    """读取窗口期数据库数据，导出文本，调用 DeepSeek 生成图表和 Markdown 报告。"""
    s = get_settings()
    base = s.output_dir
    analysis_dir = os.path.join(base, "analysis")
    charts_dir = os.path.join(base, "charts")
    reports_dir = os.path.join(base, "reports")
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(charts_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    window_tag = _safe_name(_window_tag(start_dt, end_dt))
    source_stats = get_window_source_change_stats(start_dt, end_dt)
    events = get_window_change_events(start_dt, end_dt, limit_n=500)

    payload = {
        "window": {
            "start": start_dt.isoformat(sep=" ", timespec="seconds"),
            "end": end_dt.isoformat(sep=" ", timespec="seconds"),
            "minutes": int((end_dt - start_dt).total_seconds() // 60),
        },
        "summary": {
            "source_count_with_change": len(source_stats),
            "event_count": len(events),
        },
        "source_stats": source_stats,
        "events": events,
    }
    data_txt_path = _write_window_data_file(analysis_dir, window_tag, payload)

    chart_paths, code_path = _generate_charts_by_llm(analysis_dir, charts_dir, window_tag, source_stats, events)
    if not chart_paths:
        chart_paths = _fallback_local_charts(charts_dir, window_tag, source_stats, events)

    md_path = _generate_markdown_by_llm(reports_dir, window_tag, start_dt, end_dt, source_stats, events, chart_paths)

    result = {
        "window_tag": window_tag,
        "data_txt_path": data_txt_path,
        "chart_paths": chart_paths,
        "report_md_path": md_path,
    }
    if code_path:
        result["viz_code_path"] = code_path
    return result
