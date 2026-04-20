import json
import os
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# 读取JSON数据
input_path = r"outputs\analysis\window_20260420_174748_20260420_182748_viz_input.json"
with open(input_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 创建输出目录
charts_dir = Path(r"outputs\charts")
charts_dir.mkdir(parents=True, exist_ok=True)

# 准备数据
df = pd.DataFrame(data)

# 图1: 各source的change_count柱状图
plt.figure(figsize=(10, 6))
source_counts = df.groupby('source')['change_count'].sum().sort_values(ascending=False)
source_counts.plot(kind='bar', color='skyblue', edgecolor='black')
plt.title('Change Count by Source')
plt.xlabel('Source')
plt.ylabel('Total Change Count')
plt.xticks(rotation=45)
plt.tight_layout()
chart1_path = charts_dir / "window_20260420_174748_20260420_182748_ai_source_changes.png"
plt.savefig(chart1_path, dpi=300)
plt.close()

# 图2: diff_ratio分布直方图
plt.figure(figsize=(10, 6))
plt.hist(df['diff_ratio'], bins=20, color='lightcoral', edgecolor='black', alpha=0.7)
plt.title('Distribution of Diff Ratio')
plt.xlabel('Diff Ratio')
plt.ylabel('Frequency')
plt.grid(True, alpha=0.3)
plt.tight_layout()
chart2_path = charts_dir / "window_20260420_174748_20260420_182748_ai_diff_ratio_hist.png"
plt.savefig(chart2_path, dpi=300)
plt.close()

# 生成图片路径列表
chart_paths = [str(chart1_path.absolute()), str(chart2_path.absolute())]

# 写入JSON文件
output_json_path = r"outputs\analysis\window_20260420_174748_20260420_182748_charts.json"
with open(output_json_path, 'w', encoding='utf-8') as f:
    json.dump(chart_paths, f, indent=2)