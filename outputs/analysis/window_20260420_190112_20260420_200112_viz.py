import json
import os
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

# 读取JSON数据
input_path = r"outputs\analysis\window_20260420_190112_20260420_200112_viz_input.json"
with open(input_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 创建输出目录
output_dir = Path(r"outputs\charts")
output_dir.mkdir(parents=True, exist_ok=True)

# 准备数据
df = pd.DataFrame(data)

# 1. 各source的change_count柱状图
plt.figure(figsize=(10, 6))
source_counts = df.groupby('source')['change_count'].sum().sort_values(ascending=False)
bars = plt.bar(source_counts.index, source_counts.values)
plt.title('Change Count by Source')
plt.xlabel('Source')
plt.ylabel('Change Count')
plt.xticks(rotation=45)
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(height)}', ha='center', va='bottom')
plt.tight_layout()
chart1_path = output_dir / "window_20260420_190112_20260420_200112_ai_source_changes.png"
plt.savefig(chart1_path, dpi=300)
plt.close()

# 2. diff_ratio分布直方图
plt.figure(figsize=(10, 6))
valid_ratios = df['diff_ratio'].dropna()
plt.hist(valid_ratios, bins=20, edgecolor='black', alpha=0.7)
plt.title('Distribution of Diff Ratio')
plt.xlabel('Diff Ratio')
plt.ylabel('Frequency')
plt.grid(True, alpha=0.3)
plt.tight_layout()
chart2_path = output_dir / "window_20260420_190112_20260420_200112_ai_diff_ratio_hist.png"
plt.savefig(chart2_path, dpi=300)
plt.close()

# 保存图片路径到JSON
charts_json_path = r"outputs\analysis\window_20260420_190112_20260420_200112_charts.json"
charts_data = [str(chart1_path.absolute()), str(chart2_path.absolute())]
with open(charts_json_path, 'w', encoding='utf-8') as f:
    json.dump(charts_data, f, indent=2)