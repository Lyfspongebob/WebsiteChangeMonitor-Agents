import argparse
import json
import time
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from app.db import ensure_output_dirs, fetch_enabled_sources
from app.graph.workflow import build_workflow
from app.services.analyzer import analyze_source
from app.services.reporter import build_report
from app.services.visualizer import build_charts
from app.services.window_ai import run_window_ai_pipeline
from app.utils.logger import get_logger

logger = get_logger("main")


def run_single_source(src: dict):
    app = build_workflow()
    init_state = {
        "source_id": src["id"],
        "source_name": src["name"],
        "url": src["url"],
        "css_selector": src.get("css_selector") or "body",
        "errors": [],
    }
    try:
        result = app.invoke(init_state)
        logger.info(
            f"source={src['id']} 执行完成 changed={result.get('is_changed')} report={result.get('report_md_path')}"
        )
    except Exception as e:
        logger.exception(f"source={src['id']} 执行失败: {e}")


def run_once():
    ensure_output_dirs()
    sources = fetch_enabled_sources()
    if not sources:
        logger.warning("未找到启用中的source，请检查sources表")
        return
    logger.info(f"开始执行，source数量={len(sources)}")
    for src in sources:
        run_single_source(src)


def run_periodic_analysis_once():
    ensure_output_dirs()
    sources = fetch_enabled_sources()
    if not sources:
        logger.warning("未找到启用中的source，跳过周期分析")
        return
    logger.info(f"开始周期分析，source数量={len(sources)}")
    for src in sources:
        source_id = src["id"]
        source_name = src["name"]
        try:
            analytics_id, metrics, insight = analyze_source(source_id)
            chart_paths = build_charts(source_id, analytics_id, metrics)
            md_path, ppt_path = build_report(source_id, source_name, insight, chart_paths)
            logger.info(
                f"source={source_id} 周期分析完成 analytics_id={analytics_id} charts={len(chart_paths)} report={md_path} ppt={ppt_path}"
            )
        except Exception as e:
            logger.exception(f"source={source_id} 周期分析失败: {e}")


def run_scheduler(default_interval_minutes: int, analysis_interval_minutes: int):
    scheduler = BlockingScheduler()
    ensure_output_dirs()
    sources = fetch_enabled_sources()
    if not sources:
        logger.warning("未找到启用中的source，请检查sources表")
        return

    for src in sources:
        sid = src["id"]
        interval = int(src.get("check_interval_minutes") or default_interval_minutes)
        if interval <= 0:
            interval = default_interval_minutes
        scheduler.add_job(
            run_single_source,
            "interval",
            minutes=interval,
            id=f"source_job_{sid}",
            kwargs={"src": src},
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        logger.info(f"已注册source任务 source={sid} interval={interval}分钟")

    scheduler.add_job(
        run_periodic_analysis_once,
        "interval",
        minutes=analysis_interval_minutes,
        id="periodic_analysis_job",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )
    logger.info(f"已注册周期分析任务 interval={analysis_interval_minutes}分钟")
    logger.info("定时任务已启动：按source独立间隔抓取 + 周期分析")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，调度器停止")


def run_window_session(duration_minutes: int, default_interval_minutes: int):
    """运行固定时长窗口采集，结束后统一调用 DeepSeek 生成图表和 Markdown 报告。"""
    ensure_output_dirs()
    sources = fetch_enabled_sources()
    if not sources:
        logger.warning("未找到启用中的source，请检查sources表")
        return

    start_dt = datetime.now()
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    logger.info(
        f"开始窗口采集：duration={duration_minutes}分钟 source数量={len(sources)} 窗口=[{start_dt.isoformat(sep=' ', timespec='seconds')} ~ {end_dt.isoformat(sep=' ', timespec='seconds')}]"
    )

    # 先执行一次，建立基线快照
    for src in sources:
        run_single_source(src)

    scheduler = BackgroundScheduler()
    for src in sources:
        sid = src["id"]
        interval = int(src.get("check_interval_minutes") or default_interval_minutes)
        if interval <= 0:
            interval = default_interval_minutes
        scheduler.add_job(
            run_single_source,
            "interval",
            minutes=interval,
            kwargs={"src": src},
            id=f"window_source_job_{sid}",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )
        logger.info(f"窗口任务已注册 source={sid} interval={interval}分钟")

    scheduler.start()
    try:
        while datetime.now() < end_dt:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)

    logger.info("窗口采集结束，开始生成窗口分析文件/图表/报告")
    result = run_window_ai_pipeline(start_dt, end_dt)
    logger.info(f"窗口分析结果：{json.dumps(result, ensure_ascii=False)}")


def parse_args():
    parser = argparse.ArgumentParser(description="网站变更监控多Agent系统")
    parser.add_argument("--run-once", action="store_true", help="执行一次")
    parser.add_argument("--run-analysis-once", action="store_true", help="仅执行一次周期分析并生成报告")
    parser.add_argument("--run-window-session", action="store_true", help="按窗口时长执行采集，结束后统一生成AI图表和AI报告")
    parser.add_argument("--interval-minutes", type=int, default=30, help="定时执行间隔（分钟）")
    parser.add_argument("--analysis-interval-minutes", type=int, default=60, help="周期分析任务间隔（分钟）")
    parser.add_argument("--duration-minutes", type=int, default=60, help="窗口采集持续时长（分钟）")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.run_once:
        run_once()
    elif args.run_analysis_once:
        run_periodic_analysis_once()
    elif args.run_window_session:
        run_window_session(args.duration_minutes, args.interval_minutes)
    else:
        run_scheduler(args.interval_minutes, args.analysis_interval_minutes)
