from typing import TypedDict


class AgentState(TypedDict, total=False):
    source_id: int
    source_name: str
    url: str
    css_selector: str

    raw_html: str
    raw_text: str
    content_hash: str
    snapshot_id: int
    old_snapshot_id: int

    is_changed: bool
    diff_ratio: float
    diff_summary: str
    change_event_id: int

    extracted_data: dict
    record_key: str

    analytics_id: int
    metrics: dict
    insight: str

    chart_paths: list[str]
    report_md_path: str
    ppt_path: str

    errors: list[str]
