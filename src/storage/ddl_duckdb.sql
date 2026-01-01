CREATE TABLE IF NOT EXISTS runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    source VARCHAR, -- "arcgis_online" or "portal"
    portal_url VARCHAR,
    org_id VARCHAR,
    triggered_by VARCHAR, -- "manual" or "schedule"
    pipeline_version VARCHAR
);

CREATE TABLE IF NOT EXISTS items_current (
    item_id VARCHAR PRIMARY KEY,
    title VARCHAR,
    item_type VARCHAR,
    owner VARCHAR,
    url VARCHAR,
    access VARCHAR,
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    tags_json JSON,
    tags_count INTEGER,
    snippet VARCHAR,
    snippet_len INTEGER,
    description VARCHAR,
    description_len INTEGER,
    thumbnail VARCHAR,
    has_thumbnail BOOLEAN,
    extent_xmin DOUBLE,
    extent_ymin DOUBLE,
    extent_xmax DOUBLE,
    extent_ymax DOUBLE,
    has_extent BOOLEAN,
    has_description BOOLEAN,
    num_views BIGINT,
    content_hash VARCHAR,
    last_seen_run_id UUID,
    last_seen_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS items_history (
    item_id VARCHAR,
    content_hash VARCHAR,
    valid_from TIMESTAMP,
    valid_to TIMESTAMP,
    is_current BOOLEAN,
    title VARCHAR,
    item_type VARCHAR,
    owner VARCHAR,
    url VARCHAR,
    access VARCHAR,
    modified_at TIMESTAMP,
    tags_json JSON,
    description_len INTEGER,
    has_extent BOOLEAN,
    extent_xmin DOUBLE,
    extent_ymin DOUBLE,
    extent_xmax DOUBLE,
    extent_ymax DOUBLE,
    first_seen_run_id UUID,
    last_seen_run_id UUID
);

CREATE TABLE IF NOT EXISTS quality_scores (
    run_id UUID,
    item_id VARCHAR,
    score INTEGER,
    breakdown_json JSON,
    missing_json JSON,
    computed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS health_checks (
    run_id UUID,
    item_id VARCHAR,
    checked_url VARCHAR,
    ok BOOLEAN,
    status_code INTEGER,
    latency_ms INTEGER,
    error_message VARCHAR,
    checked_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS relationships (
    run_id UUID,
    src_item_id VARCHAR,
    dst_item_id VARCHAR,
    relationship_type VARCHAR
);
