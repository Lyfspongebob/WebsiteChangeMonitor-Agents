import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.config import get_settings
from app.db import insert_visual_asset

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  #  Windows黑体
# 或使用 ['Microsoft YaHei'] 微软雅黑
# 或使用 ['Arial Unicode MS']  # macOS

# 解决负号显示问题
plt.rcParams['axes.unicode_minus'] = False

def build_charts(source_id: int, analytics_id: int, metrics: dict) -> list[str]:
    out_dir = os.path.join(get_settings().output_dir, "charts")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    chart_paths: list[str] = []

    change_data = metrics.get("changes_last_7_days", [])
    dates = [str(x.get("d")) for x in change_data]
    counts = [int(x.get("c", 0)) for x in change_data]

    fig1 = plt.figure(figsize=(8, 4))
    plt.plot(dates, counts, marker="o")
    plt.title("最近7天变更趋势")
    plt.xlabel("日期")
    plt.ylabel("变更次数")
    plt.xticks(rotation=30)
    plt.tight_layout()
    p1 = os.path.join(out_dir, f"source_{source_id}_{ts}_trend.png")
    fig1.savefig(p1)
    plt.close(fig1)
    chart_paths.append(p1)
    insert_visual_asset(analytics_id, "trend", p1)

    cumulative = []
    total = 0
    for c in counts:
        total += c
        cumulative.append(total)
    fig2 = plt.figure(figsize=(8, 4))
    plt.bar(dates, cumulative)
    plt.title("累计变更次数")
    plt.xlabel("日期")
    plt.ylabel("累计次数")
    plt.xticks(rotation=30)
    plt.tight_layout()
    p2 = os.path.join(out_dir, f"source_{source_id}_{ts}_cumulative.png")
    fig2.savefig(p2)
    plt.close(fig2)
    chart_paths.append(p2)
    insert_visual_asset(analytics_id, "cumulative", p2)

    top_data = metrics.get("top_records_last_30_days", [])
    labels = [str(x.get("k", "unknown"))[:15] for x in top_data]
    vals = [int(x.get("c", 0)) for x in top_data]
    fig3 = plt.figure(figsize=(8, 4))
    plt.barh(labels, vals)
    plt.title("Top记录出现频次")
    plt.xlabel("次数")
    plt.tight_layout()
    p3 = os.path.join(out_dir, f"source_{source_id}_{ts}_top.png")
    fig3.savefig(p3)
    plt.close(fig3)
    chart_paths.append(p3)
    insert_visual_asset(analytics_id, "top_records", p3)

    return chart_paths
