# 网站变更监控多Agent系统（LangGraph + DeepSeek + MySQL）

本项目用于数据可视化课程作业，支持：

- 网站/接口内容监控（触发式）
- 发现变化后自动抽取关键数据并入 MySQL
- 自动分析并生成图表（PNG）
- 自动生成报告（Markdown）和 PPT
- 多 Agent 协同（LangGraph 工作流）

---

## 1. 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

复制环境变量文件：

```bash
copy .env.example .env
```

填写 `.env` 中：

- `DEEPSEEK_API_KEY`
- MySQL 连接信息

---

## 2. 初始化数据库

你已建好数据库时，至少执行建表和种子数据：

```bash
mysql -u root -p web_monitor < sql/01_init.sql
mysql -u root -p web_monitor < sql/02_seed_sources.sql
```

---

## 3. 运行方式

### 单次运行（推荐演示）

```bash
python -m app.main --run-once
```

### 定时运行

```bash
python -m app.main --run-window-session --duration-minutes 60 --interval-minutes 5
```

---

## 4. 输出目录

程序将自动输出到：

- `outputs/snapshots/`：网页快照
- `outputs/charts/`：可视化图表
- `outputs/reports/`：markdown 报告
- `outputs/ppt/`：自动生成 PPT
- `outputs/analysis/`：窗口分析中间文件（AI输入数据、AI生成绘图脚本、图表索引）

### 4.1 各目录详细解释

#### `outputs/snapshots/`
- 保存每次抓取的原始 HTML 快照（留痕、回溯、排障）。
- 常见文件名：`source_3_20260420_190656.html`

#### `outputs/charts/`
- 保存可视化图片（PNG）。
- 分两类：
  - 单站点图：`source_*_trend.png` / `source_*_cumulative.png` / `source_*_top.png`
  - 窗口聚合图：`window_*_by_source.png` / `window_*_diff_ratio_dist.png`

#### `outputs/reports/`
- 保存 Markdown 报告。
- 分两类：
  - 单站点即时报告：`source_*_*.md`
  - 窗口聚合 AI 报告：`window_*_ai_report.md`

#### `outputs/ppt/`
- 保存自动生成的 PPT 报告（当前以单站点报告为主）。

#### `outputs/analysis/`
- 保存窗口分析过程文件（用于“文本喂给 AI -> 出图/出报告”链路）：
  - `window_*_data.txt`：窗口统计原始文本
  - `window_*_viz_input.json`：AI绘图输入数据
  - `window_*_viz.py`：AI生成的绘图脚本
  - `window_*_charts.json`：绘图结果路径索引

### 4.2 如何判断一次窗口任务是否完整成功

同一个 `window_<start>_<end>` 标签下，若同时存在：
- `outputs/analysis/window_*_data.txt`
- `outputs/charts/window_*...png`
- `outputs/reports/window_*_ai_report.md`

则说明“采集 -> 分析 -> 可视化 -> 报告”全链路已跑通。

---

## 5. 工作流（Agent）

`watch -> diff -> extract -> integrate -> analyze -> visualize -> report -> reflect`

其中 `reflect` 为“自我进化”节点：对抽取失败样本自动生成 prompt 改进建议并存库。
