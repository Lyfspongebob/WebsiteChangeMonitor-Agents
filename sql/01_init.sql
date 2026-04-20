CREATE TABLE IF NOT EXISTS sources (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  url TEXT NOT NULL,
  css_selector VARCHAR(255) NULL,
  check_interval_minutes INT DEFAULT 60,
  enabled TINYINT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS snapshots (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_id BIGINT NOT NULL,
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  content_hash CHAR(64) NOT NULL,
  raw_text LONGTEXT,
  raw_html_path VARCHAR(500),
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS change_events (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_id BIGINT NOT NULL,
  old_snapshot_id BIGINT,
  new_snapshot_id BIGINT NOT NULL,
  diff_ratio DECIMAL(6,4),
  diff_summary TEXT,
  triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status VARCHAR(50) DEFAULT 'detected',
  FOREIGN KEY (source_id) REFERENCES sources(id),
  FOREIGN KEY (old_snapshot_id) REFERENCES snapshots(id),
  FOREIGN KEY (new_snapshot_id) REFERENCES snapshots(id)
);

CREATE TABLE IF NOT EXISTS extracted_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  change_event_id BIGINT NOT NULL,
  record_key VARCHAR(255),
  field_json JSON NOT NULL,
  extractor_version VARCHAR(50),
  extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (change_event_id) REFERENCES change_events(id)
);

CREATE TABLE IF NOT EXISTS analytics_results (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_id BIGINT NOT NULL,
  period_start DATETIME,
  period_end DATETIME,
  metrics_json JSON,
  insight_text TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS visual_assets (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  analytics_id BIGINT NOT NULL,
  chart_type VARCHAR(100),
  file_path VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analytics_id) REFERENCES analytics_results(id)
);

CREATE TABLE IF NOT EXISTS reports (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  source_id BIGINT NOT NULL,
  report_md_path VARCHAR(500),
  pptx_path VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (source_id) REFERENCES sources(id)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  agent_name VARCHAR(100) NOT NULL,
  prompt_text TEXT NOT NULL,
  score DECIMAL(6,4),
  is_active TINYINT DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
