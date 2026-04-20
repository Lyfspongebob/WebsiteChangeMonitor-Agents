import json
import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.config import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    s = get_settings()
    dsn = (
        f"mysql+pymysql://{s.mysql_user}:{s.mysql_password}"
        f"@{s.mysql_host}:{s.mysql_port}/{s.mysql_db}?charset=utf8mb4"
    )
    _engine = create_engine(dsn, pool_pre_ping=True)

    # 启动时做一次连通性探测，便于给出更清晰的配置提示
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        raise RuntimeError(
            "数据库连接失败，请检查 .env 中 MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB 是否正确，"
            "并确认 MySQL 服务已启动。"
        ) from e

    return _engine


def ensure_output_dirs() -> None:
    base = get_settings().output_dir
    for sub in ["snapshots", "charts", "reports", "ppt", "analysis"]:
        os.makedirs(os.path.join(base, sub), exist_ok=True)


def fetch_enabled_sources() -> list[dict]:
    sql = text("SELECT id, name, url, css_selector, check_interval_minutes FROM sources WHERE enabled = 1")
    with get_engine().connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [dict(r) for r in rows]


def get_latest_snapshot(source_id: int) -> dict | None:
    sql = text(
        """
        SELECT id, source_id, fetched_at, content_hash, raw_text, raw_html_path
        FROM snapshots
        WHERE source_id = :sid
        ORDER BY id DESC
        LIMIT 1
        """
    )
    with get_engine().connect() as conn:
        row = conn.execute(sql, {"sid": source_id}).mappings().first()
    return dict(row) if row else None


def get_snapshot_by_id(snapshot_id: int) -> dict | None:
    sql = text(
        """
        SELECT id, source_id, fetched_at, content_hash, raw_text, raw_html_path
        FROM snapshots
        WHERE id = :id
        LIMIT 1
        """
    )
    with get_engine().connect() as conn:
        row = conn.execute(sql, {"id": snapshot_id}).mappings().first()
    return dict(row) if row else None


def insert_snapshot(source_id: int, content_hash: str, raw_text: str, raw_html_path: str) -> int:
    sql = text(
        """
        INSERT INTO snapshots (source_id, content_hash, raw_text, raw_html_path)
        VALUES (:sid, :h, :t, :p)
        """
    )
    with get_engine().begin() as conn:
        result = conn.execute(sql, {"sid": source_id, "h": content_hash, "t": raw_text, "p": raw_html_path})
        return int(result.lastrowid)


def create_change_event(
    source_id: int,
    old_snapshot_id: int | None,
    new_snapshot_id: int,
    diff_ratio: float,
    diff_summary: str,
    status: str = "detected",
) -> int:
    sql = text(
        """
        INSERT INTO change_events (source_id, old_snapshot_id, new_snapshot_id, diff_ratio, diff_summary, status)
        VALUES (:sid, :old_id, :new_id, :ratio, :summary, :status)
        """
    )
    with get_engine().begin() as conn:
        result = conn.execute(
            sql,
            {
                "sid": source_id,
                "old_id": old_snapshot_id,
                "new_id": new_snapshot_id,
                "ratio": diff_ratio,
                "summary": diff_summary,
                "status": status,
            },
        )
        return int(result.lastrowid)


def update_change_event_status(event_id: int, status: str):
    sql = text("UPDATE change_events SET status=:s WHERE id=:id")
    with get_engine().begin() as conn:
        conn.execute(sql, {"s": status, "id": event_id})


def insert_extracted_record(change_event_id: int, record_key: str, field_json: dict, extractor_version: str):
    sql = text(
        """
        INSERT INTO extracted_records (change_event_id, record_key, field_json, extractor_version)
        VALUES (:cid, :rk, CAST(:fj AS JSON), :v)
        """
    )
    with get_engine().begin() as conn:
        conn.execute(
            sql,
            {
                "cid": change_event_id,
                "rk": record_key,
                "fj": json.dumps(field_json, ensure_ascii=False,default=str),
                "v": extractor_version,
            },
        )


def insert_analytics_result(source_id: int, period_start: datetime, period_end: datetime, metrics_json: dict, insight_text: str) -> int:
    sql = text(
        """
        INSERT INTO analytics_results (source_id, period_start, period_end, metrics_json, insight_text)
        VALUES (:sid, :ps, :pe, CAST(:m AS JSON), :i)
        """
    )
    with get_engine().begin() as conn:
        result = conn.execute(
            sql,
            {
                "sid": source_id,
                "ps": period_start,
                "pe": period_end,
                "m": json.dumps(metrics_json, ensure_ascii=False, default=str),
                "i": insight_text,
            },
        )
        return int(result.lastrowid)


def insert_visual_asset(analytics_id: int, chart_type: str, file_path: str):
    sql = text(
        "INSERT INTO visual_assets (analytics_id, chart_type, file_path) VALUES (:aid, :t, :p)"
    )
    with get_engine().begin() as conn:
        conn.execute(sql, {"aid": analytics_id, "t": chart_type, "p": file_path})


def insert_report(source_id: int, report_md_path: str, pptx_path: str):
    sql = text("INSERT INTO reports (source_id, report_md_path, pptx_path) VALUES (:sid, :md, :ppt)")
    with get_engine().begin() as conn:
        conn.execute(sql, {"sid": source_id, "md": report_md_path, "ppt": pptx_path})


def get_change_counts_last_days(source_id: int, days: int = 7) -> list[dict]:
    start_date = datetime.now() - timedelta(days=days)
    sql = text(
        """
        SELECT DATE(triggered_at) AS d, COUNT(*) AS c
        FROM change_events
        WHERE source_id=:sid AND triggered_at >= :start_dt
        GROUP BY DATE(triggered_at)
        ORDER BY d ASC
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"sid": source_id, "start_dt": start_date}).mappings().all()
    return [dict(r) for r in rows]


def get_keyword_like_counts(source_id: int, days: int = 30) -> list[dict]:
    start_date = datetime.now() - timedelta(days=days)
    sql = text(
        """
        SELECT er.record_key AS k, COUNT(*) AS c
        FROM extracted_records er
        JOIN change_events ce ON er.change_event_id = ce.id
        WHERE ce.source_id=:sid AND er.extracted_at >= :start_dt
        GROUP BY er.record_key
        ORDER BY c DESC
        LIMIT 10
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"sid": source_id, "start_dt": start_date}).mappings().all()
    return [dict(r) for r in rows]


def get_recent_extraction_failures(limit_n: int = 10) -> list[dict]:
    sql = text(
        """
        SELECT id, source_id, diff_summary, status, triggered_at
        FROM change_events
        WHERE status IN ('extract_failed', 'extract_invalid')
        ORDER BY id DESC
        LIMIT :n
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"n": limit_n}).mappings().all()
    return [dict(r) for r in rows]


def save_prompt_version(agent_name: str, prompt_text: str, score: float, is_active: int = 1):
    sql = text(
        """
        INSERT INTO prompt_versions (agent_name, prompt_text, score, is_active)
        VALUES (:a, :p, :s, :i)
        """
    )
    with get_engine().begin() as conn:
        conn.execute(sql, {"a": agent_name, "p": prompt_text, "s": score, "i": is_active})


def get_window_source_change_stats(start_dt: datetime, end_dt: datetime) -> list[dict]:
    sql = text(
        """
        SELECT
            ce.source_id AS source_id,
            s.name AS source_name,
            COUNT(*) AS change_count,
            AVG(ce.diff_ratio) AS avg_diff_ratio,
            MAX(ce.diff_ratio) AS max_diff_ratio
        FROM change_events ce
        JOIN sources s ON ce.source_id = s.id
        WHERE ce.triggered_at >= :start_dt AND ce.triggered_at < :end_dt
        GROUP BY ce.source_id, s.name
        ORDER BY change_count DESC, ce.source_id ASC
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"start_dt": start_dt, "end_dt": end_dt}).mappings().all()
    return [dict(r) for r in rows]


def get_window_change_events(start_dt: datetime, end_dt: datetime, limit_n: int = 200) -> list[dict]:
    sql = text(
        """
        SELECT
            ce.id,
            ce.source_id,
            s.name AS source_name,
            ce.diff_ratio,
            ce.diff_summary,
            ce.status,
            ce.triggered_at
        FROM change_events ce
        JOIN sources s ON ce.source_id = s.id
        WHERE ce.triggered_at >= :start_dt AND ce.triggered_at < :end_dt
        ORDER BY ce.triggered_at ASC
        LIMIT :n
        """
    )
    with get_engine().connect() as conn:
        rows = conn.execute(sql, {"start_dt": start_dt, "end_dt": end_dt, "n": limit_n}).mappings().all()
    return [dict(r) for r in rows]
