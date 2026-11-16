-- AudienceIQ PK canonical schema (SQLite dialect; Postgres-compatible apart from type affinity).
-- Every dataset bundle is loaded through these constraints with PRAGMA foreign_keys = ON.

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id        TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    mode              TEXT NOT NULL CHECK (mode IN ('synthetic', 'observed', 'imported')),
    description       TEXT,
    product_category  TEXT,
    created_at        TEXT NOT NULL,
    snapshot_at       TEXT NOT NULL,
    expires_at        TEXT,
    seed              INTEGER,
    generator_version TEXT,
    text_permission   TEXT NOT NULL CHECK (text_permission IN ('full', 'illustrative', 'withheld')),
    disclaimer        TEXT NOT NULL,
    post_count        INTEGER NOT NULL CHECK (post_count >= 0),
    comment_count     INTEGER NOT NULL CHECK (comment_count >= 0),
    manifest_json     TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    source_id         TEXT NOT NULL,
    dataset_id        TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    source_type       TEXT NOT NULL,
    name              TEXT NOT NULL,
    url               TEXT,
    collection_method TEXT NOT NULL,
    collected_at      TEXT,
    reuse_permission  TEXT NOT NULL,
    notes             TEXT,
    PRIMARY KEY (dataset_id, source_id)
);

CREATE TABLE IF NOT EXISTS campaigns (
    dataset_id      TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    campaign_id     TEXT NOT NULL,
    name            TEXT NOT NULL,
    campaign_type   TEXT NOT NULL,
    start_date      TEXT,
    end_date        TEXT,
    campaign_source TEXT NOT NULL,
    PRIMARY KEY (dataset_id, campaign_id)
);

CREATE TABLE IF NOT EXISTS posts (
    dataset_id            TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    post_id               TEXT NOT NULL,
    source_id             TEXT NOT NULL,
    source_post_id        TEXT NOT NULL,
    brand                 TEXT NOT NULL,
    platform              TEXT NOT NULL CHECK (platform IN ('Instagram', 'TikTok', 'Facebook', 'YouTube', 'Other')),
    campaign_id           TEXT,
    campaign              TEXT NOT NULL,
    content_type          TEXT NOT NULL CHECK (content_type IN
                          ('reel', 'video', 'product_photo', 'influencer_post', 'styling_video', 'sale_announcement', 'other', 'unknown')),
    content_type_raw      TEXT,
    product_category      TEXT NOT NULL,
    likes                 INTEGER CHECK (likes IS NULL OR likes >= 0),
    comments_count        INTEGER CHECK (comments_count IS NULL OR comments_count >= 0),
    shares                INTEGER CHECK (shares IS NULL OR shares >= 0),
    views                 INTEGER CHECK (views IS NULL OR views >= 0),
    published_at          TEXT NOT NULL,
    snapshot_at           TEXT NOT NULL,
    days_since_post       INTEGER NOT NULL CHECK (days_since_post >= 0),
    source_url            TEXT,
    source_type           TEXT NOT NULL,
    dataset_origin        TEXT NOT NULL,
    collection_method     TEXT NOT NULL,
    reuse_permission      TEXT NOT NULL,
    observed_vs_synthetic TEXT NOT NULL CHECK (observed_vs_synthetic IN ('observed', 'synthetic', 'imported')),
    post_text             TEXT,
    PRIMARY KEY (dataset_id, post_id),
    UNIQUE (platform, source_post_id, dataset_id),
    FOREIGN KEY (dataset_id, source_id) REFERENCES sources(dataset_id, source_id),
    FOREIGN KEY (dataset_id, campaign_id) REFERENCES campaigns(dataset_id, campaign_id)
);
CREATE INDEX IF NOT EXISTS ix_posts_filters ON posts (dataset_id, platform, brand, content_type, campaign);

CREATE TABLE IF NOT EXISTS comments (
    dataset_id        TEXT NOT NULL,
    comment_id        TEXT NOT NULL,
    post_id           TEXT NOT NULL,
    comment_text      TEXT,
    text_permission   TEXT NOT NULL CHECK (text_permission IN ('full', 'illustrative', 'withheld')),
    language_type     TEXT NOT NULL CHECK (language_type IN ('english', 'roman_urdu', 'urdu', 'mixed', 'other', 'unknown')),
    topic             TEXT NOT NULL,
    topic_confidence  REAL CHECK (topic_confidence IS NULL OR (topic_confidence >= 0 AND topic_confidence <= 1)),
    sentiment         TEXT NOT NULL CHECK (sentiment IN ('positive', 'neutral', 'negative', 'unknown')),
    purchase_intent   TEXT NOT NULL CHECK (purchase_intent IN ('strong_intent', 'possible_inquiry', 'none', 'unknown')),
    published_at      TEXT,
    like_count        INTEGER CHECK (like_count IS NULL OR like_count >= 0),
    char_len          INTEGER NOT NULL CHECK (char_len >= 0),
    source            TEXT NOT NULL,
    PRIMARY KEY (dataset_id, comment_id),
    FOREIGN KEY (dataset_id, post_id) REFERENCES posts(dataset_id, post_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_comments_post ON comments (dataset_id, post_id);

CREATE TABLE IF NOT EXISTS cluster_runs (
    run_id            TEXT PRIMARY KEY,
    dataset_id        TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    created_at        TEXT NOT NULL,
    embedding         TEXT NOT NULL,
    embedding_model   TEXT NOT NULL,
    algorithm         TEXT NOT NULL,
    params_json       TEXT NOT NULL,
    seed              INTEGER NOT NULL,
    n_comments        INTEGER NOT NULL CHECK (n_comments >= 0),
    n_clusters        INTEGER NOT NULL CHECK (n_clusters >= 0),
    noise_rate        REAL NOT NULL CHECK (noise_rate >= 0 AND noise_rate <= 1),
    metrics_json      TEXT NOT NULL,
    selected          INTEGER NOT NULL CHECK (selected IN (0, 1)),
    model_version     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cluster_runs_dataset ON cluster_runs (dataset_id, selected);

CREATE TABLE IF NOT EXISTS cluster_assignments (
    run_id       TEXT NOT NULL REFERENCES cluster_runs(run_id) ON DELETE CASCADE,
    dataset_id   TEXT NOT NULL,
    comment_id   TEXT NOT NULL,
    cluster_id   INTEGER NOT NULL,
    distance     REAL,
    is_noise     INTEGER NOT NULL CHECK (is_noise IN (0, 1)),
    PRIMARY KEY (run_id, comment_id),
    FOREIGN KEY (dataset_id, comment_id) REFERENCES comments(dataset_id, comment_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_assign_cluster ON cluster_assignments (run_id, cluster_id);

CREATE TABLE IF NOT EXISTS cluster_profiles (
    run_id            TEXT NOT NULL REFERENCES cluster_runs(run_id) ON DELETE CASCADE,
    cluster_id        INTEGER NOT NULL,
    label             TEXT NOT NULL,
    need_category     TEXT NOT NULL,
    label_source      TEXT NOT NULL,
    label_agreement   REAL NOT NULL CHECK (label_agreement >= 0 AND label_agreement <= 1),
    size              INTEGER NOT NULL CHECK (size >= 0),
    share             REAL NOT NULL CHECK (share >= 0 AND share <= 1),
    cohesion          REAL,
    top_terms_json    TEXT NOT NULL,
    language_mix_json TEXT NOT NULL,
    need_mix_json     TEXT NOT NULL,
    exemplars_json    TEXT NOT NULL,
    date_min          TEXT,
    date_max          TEXT,
    explanation       TEXT NOT NULL,
    PRIMARY KEY (run_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS anomaly_runs (
    run_id         TEXT PRIMARY KEY,
    dataset_id     TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    created_at     TEXT NOT NULL,
    method         TEXT NOT NULL,
    params_json    TEXT NOT NULL,
    n_posts_scored INTEGER NOT NULL CHECK (n_posts_scored >= 0),
    n_flagged      INTEGER NOT NULL CHECK (n_flagged >= 0),
    metrics_json   TEXT NOT NULL,
    model_version  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anomaly_flags (
    flag_id         TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES anomaly_runs(run_id) ON DELETE CASCADE,
    dataset_id      TEXT NOT NULL,
    post_id         TEXT NOT NULL,
    kind            TEXT NOT NULL,
    metric          TEXT NOT NULL,
    value           REAL,
    baseline_median REAL,
    expected_low    REAL,
    expected_high   REAL,
    score           REAL NOT NULL,
    iforest_score   REAL,
    direction       TEXT NOT NULL CHECK (direction IN ('positive', 'negative')),
    cohort_key      TEXT NOT NULL,
    cohort_level    TEXT NOT NULL,
    cohort_size     INTEGER NOT NULL CHECK (cohort_size >= 0),
    severity        TEXT NOT NULL CHECK (severity IN ('high', 'medium')),
    reason          TEXT NOT NULL,
    caveat          TEXT NOT NULL,
    FOREIGN KEY (dataset_id, post_id) REFERENCES posts(dataset_id, post_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_flags_dataset ON anomaly_flags (dataset_id, kind, direction);

CREATE TABLE IF NOT EXISTS anomaly_scores (
    run_id        TEXT NOT NULL REFERENCES anomaly_runs(run_id) ON DELETE CASCADE,
    dataset_id    TEXT NOT NULL,
    post_id       TEXT NOT NULL,
    cohort_key    TEXT NOT NULL,
    cohort_level  TEXT NOT NULL,
    cohort_size   INTEGER NOT NULL,
    metric        TEXT NOT NULL,
    value         REAL,
    robust_z      REAL,
    comment_ratio_z REAL,
    iforest_score REAL,
    flagged       INTEGER NOT NULL CHECK (flagged IN (0, 1)),
    PRIMARY KEY (run_id, post_id),
    FOREIGN KEY (dataset_id, post_id) REFERENCES posts(dataset_id, post_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id TEXT NOT NULL,
    dataset_id        TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    generated_at      TEXT NOT NULL,
    action_type       TEXT NOT NULL CHECK (action_type IN ('content', 'promotion', 'customer_service', 'campaign_test', 'investigation')),
    title             TEXT NOT NULL,
    what_to_do        TEXT NOT NULL,
    why_it_matters    TEXT NOT NULL,
    audience_need     TEXT,
    where_json        TEXT NOT NULL,
    linked_evidence_json TEXT NOT NULL,
    priority          INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 3),
    evidence_strength TEXT NOT NULL CHECK (evidence_strength IN ('strong', 'moderate', 'limited')),
    sample_size       INTEGER NOT NULL CHECK (sample_size >= 0),
    metrics_json      TEXT NOT NULL,
    limitations_json  TEXT NOT NULL,
    test_plan         TEXT NOT NULL,
    PRIMARY KEY (dataset_id, recommendation_id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id      TEXT NOT NULL,
    dataset_id  TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    step        TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ok', 'skipped', 'failed')),
    started_at  TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    details_json TEXT NOT NULL,
    PRIMARY KEY (dataset_id, run_id, step)
);
