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

---

## 5. 工作流（Agent）

`watch -> diff -> extract -> integrate -> analyze -> visualize -> report -> reflect`

其中 `reflect` 为“自我进化”节点：对抽取失败样本自动生成 prompt 改进建议并存库。
