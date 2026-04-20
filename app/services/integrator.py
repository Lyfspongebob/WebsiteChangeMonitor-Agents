from app.db import insert_extracted_record


def integrate_extracted(change_event_id: int, extracted: dict, extractor_version: str = "v1") -> str:
    record_key = extracted.get("title", "untitled")[:200]
    insert_extracted_record(
        change_event_id=change_event_id,
        record_key=record_key,
        field_json=extracted,
        extractor_version=extractor_version,
    )
    return record_key
