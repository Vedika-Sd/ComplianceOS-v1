-- ============================================================
-- ComplianceOS — Complete Database Schema
-- SQLite3 | All tables, indexes, and constraints
-- ============================================================

PRAGMA journal_mode = WAL;       -- Write-Ahead Logging: safer concurrent reads
PRAGMA foreign_keys = ON;        -- Enforce FK constraints
PRAGMA auto_vacuum = INCREMENTAL; -- Keep DB file size clean

-- ============================================================
-- TABLE 1: businesses
-- Stores every business profile with full version history.
-- We never UPDATE a profile — we INSERT a new version.
-- This means old compliance analyses remain valid forever.
-- ============================================================
CREATE TABLE IF NOT EXISTS businesses (
    id                      TEXT PRIMARY KEY,          -- UUID e.g. "biz_a1b2c3d4"
    version                 INTEGER NOT NULL DEFAULT 1, -- Increments on each profile update
    is_current              INTEGER NOT NULL DEFAULT 1, -- 1 = active version, 0 = historical

    -- Identity
    business_name           TEXT NOT NULL,
    entity_type             TEXT NOT NULL,             -- "Private Limited", "LLP", etc.
    industry                TEXT NOT NULL,             -- "Digital Lending / NBFC", "Manufacturing", etc.
    state                   TEXT NOT NULL,             -- "Maharashtra", "Karnataka", etc.
    year_of_incorporation   INTEGER,

    -- Financials (all monetary values in Crore INR)
    annual_turnover_cr      REAL NOT NULL,
    projected_turnover_cr   REAL,                      -- Next FY projection (for simulation)
    digital_revenue_pct     REAL DEFAULT 0,            -- % revenue from digital channels
    b2b_sales_pct           REAL DEFAULT 0,            -- % sales to other businesses
    exports_revenue_cr      REAL DEFAULT 0,
    investment_plant_cr     REAL DEFAULT 0,            -- Investment in plant/machinery (MSME classification)
    loan_portfolio_cr       REAL DEFAULT 0,            -- Active loan book (for NBFCs)

    -- Regulatory flags (INTEGER as boolean: 1=true, 0=false)
    has_gstin               INTEGER DEFAULT 0,
    has_nbfc_license        INTEGER DEFAULT 0,
    has_pa_license          INTEGER DEFAULT 0,         -- Payment Aggregator license
    has_udyam_registration  INTEGER DEFAULT 0,
    is_listed               INTEGER DEFAULT 0,         -- Listed on stock exchange
    uses_lsp                INTEGER DEFAULT 0,         -- Uses Lending Service Provider
    has_digital_lending_app INTEGER DEFAULT 0,
    has_export_activities   INTEGER DEFAULT 0,
    has_gst_notices         INTEGER DEFAULT 0,         -- Existing GST notices/disputes
    files_einvoice          INTEGER DEFAULT 0,         -- Currently filing e-invoices

    -- Operations
    employee_count          INTEGER DEFAULT 0,
    inter_state_sales_pct   REAL DEFAULT 0,            -- % inter-state sales (affects GST)
    states_operating        TEXT DEFAULT '[]',         -- JSON array of states

    -- Contact / notification
    contact_email           TEXT,
    contact_phone           TEXT,
    alerts_enabled          INTEGER DEFAULT 1,

    -- Metadata
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now')),
    created_by              TEXT DEFAULT 'user',

    -- Constraints
    CHECK (annual_turnover_cr >= 0),
    CHECK (digital_revenue_pct BETWEEN 0 AND 100),
    CHECK (b2b_sales_pct BETWEEN 0 AND 100),
    CHECK (entity_type IN (
        'Sole Proprietorship', 'Partnership', 'LLP',
        'Private Limited', 'Public Limited', 'OPC', 'Trust', 'Society'
    ))
);

CREATE INDEX IF NOT EXISTS idx_businesses_current ON businesses(id, is_current);
CREATE INDEX IF NOT EXISTS idx_businesses_industry ON businesses(industry);
CREATE INDEX IF NOT EXISTS idx_businesses_turnover ON businesses(annual_turnover_cr);


-- ============================================================
-- TABLE 2: thresholds
-- The deterministic rule engine.
-- Every compliance rule is a row here — no LLM involved.
-- When regulations change, we INSERT new rows with effective_to on old ones.
-- ============================================================
CREATE TABLE IF NOT EXISTS thresholds (
    id                  TEXT PRIMARY KEY,              -- e.g. "GST-002-v1"
    rule_id             TEXT NOT NULL,                 -- e.g. "GST-002" (stable across versions)
    version             INTEGER NOT NULL DEFAULT 1,

    -- Rule definition
    regulator           TEXT NOT NULL,                 -- "GST", "RBI", "SEBI", "MSME"
    category            TEXT NOT NULL,                 -- "Registration", "E-Invoicing", "Digital Lending", etc.
    obligation_title    TEXT NOT NULL,
    obligation_desc     TEXT NOT NULL,                 -- Plain English description

    -- Condition (what triggers this rule)
    condition_field     TEXT NOT NULL,                 -- Business profile field name
    operator            TEXT NOT NULL,                 -- ">=", "<=", "==", ">", "<", "!="
    condition_value     TEXT NOT NULL,                 -- The threshold value (stored as text, cast at runtime)
    condition_type      TEXT NOT NULL DEFAULT 'numeric', -- "numeric", "boolean", "string"

    -- Additional conditions (AND logic — all must be true)
    condition_field_2   TEXT,                          -- Optional second condition
    operator_2          TEXT,
    condition_value_2   TEXT,
    condition_type_2    TEXT,

    -- Obligation details
    priority            TEXT NOT NULL DEFAULT 'MEDIUM', -- "HIGH", "MEDIUM", "LOW"
    deadline_type       TEXT NOT NULL,                 -- "One-time", "Monthly", "Quarterly", "Annual", "Continuous"
    deadline_days       INTEGER,                       -- Days to comply after triggering
    estimated_penalty_inr REAL DEFAULT 0,             -- Maximum penalty for non-compliance
    penalty_description TEXT,                          -- How penalty is calculated
    action_steps        TEXT DEFAULT '[]',             -- JSON array of action steps
    citation            TEXT NOT NULL,                 -- Exact regulation reference
    citation_url        TEXT,                          -- URL to source document

    -- Versioning / effective dates
    effective_from      TEXT NOT NULL,                 -- When this rule became effective
    effective_to        TEXT,                          -- NULL = currently active
    is_active           INTEGER NOT NULL DEFAULT 1,

    -- For simulation
    affects_msme_class  INTEGER DEFAULT 0,             -- Does this affect MSME classification?
    is_benefit          INTEGER DEFAULT 0,             -- 1 = benefit (not obligation)

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (regulator IN ('GST', 'RBI', 'SEBI', 'MSME', 'MCA', 'IT', 'PF_ESI')),
    CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    CHECK (operator IN ('>=', '<=', '==', '>', '<', '!=')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_thresholds_regulator ON thresholds(regulator, is_active);
CREATE INDEX IF NOT EXISTS idx_thresholds_rule_id ON thresholds(rule_id);
CREATE INDEX IF NOT EXISTS idx_thresholds_active ON thresholds(is_active, effective_from);


-- ============================================================
-- TABLE 3: obligations
-- Triggered obligations per business — output of the Analyst Agent.
-- ============================================================
CREATE TABLE IF NOT EXISTS obligations (
    id                  TEXT PRIMARY KEY,              -- UUID e.g. "obl_x1y2z3"
    business_id         TEXT NOT NULL,
    business_version    INTEGER NOT NULL,              -- Which version of the profile triggered this
    threshold_id        TEXT NOT NULL,                 -- Which rule triggered this
    analysis_session_id TEXT NOT NULL,                 -- Groups all obligations from one analysis run

    -- Status
    status              TEXT NOT NULL DEFAULT 'OPEN',  -- "OPEN", "IN_PROGRESS", "COMPLIANT", "WAIVED", "ESCALATED"
    applicability       TEXT NOT NULL DEFAULT 'APPLICABLE', -- "APPLICABLE", "NOT_APPLICABLE", "CONDITIONAL"
    confidence          REAL DEFAULT 1.0,              -- 0.0-1.0 confidence in applicability decision

    -- Details (copied from threshold for immutability)
    regulator           TEXT NOT NULL,
    category            TEXT NOT NULL,
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    priority            TEXT NOT NULL,
    deadline_type       TEXT NOT NULL,
    due_date            TEXT,                          -- Computed actual deadline date
    estimated_penalty_inr REAL DEFAULT 0,
    citation            TEXT NOT NULL,
    action_steps        TEXT DEFAULT '[]',             -- JSON array

    -- LLM-generated content
    llm_explanation     TEXT,                          -- Plain English explanation for this business
    llm_recommendations TEXT,                          -- Specific recommendations
    needs_human_review  INTEGER DEFAULT 0,             -- 1 = flag for human approval
    human_review_reason TEXT,

    -- Agent metadata
    triggered_by_agent  TEXT DEFAULT 'AnalystAgent',
    analysis_method     TEXT DEFAULT 'rule_based',     -- "rule_based", "rag", "hybrid"

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (business_id) REFERENCES businesses(id),
    FOREIGN KEY (threshold_id) REFERENCES thresholds(id),
    CHECK (status IN ('OPEN', 'IN_PROGRESS', 'COMPLIANT', 'WAIVED', 'ESCALATED')),
    CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW')),
    CHECK (confidence BETWEEN 0.0 AND 1.0)
);

CREATE INDEX IF NOT EXISTS idx_obligations_business ON obligations(business_id, status);
CREATE INDEX IF NOT EXISTS idx_obligations_session ON obligations(analysis_session_id);
CREATE INDEX IF NOT EXISTS idx_obligations_priority ON obligations(priority, status);
CREATE INDEX IF NOT EXISTS idx_obligations_due ON obligations(due_date);


-- ============================================================
-- TABLE 4: action_items
-- Task list generated by Action Agent for each obligation.
-- ============================================================
CREATE TABLE IF NOT EXISTS action_items (
    id                  TEXT PRIMARY KEY,              -- e.g. "act_a1b2c3"
    obligation_id       TEXT NOT NULL,
    business_id         TEXT NOT NULL,
    step_number         INTEGER NOT NULL DEFAULT 1,

    -- Task details
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    category            TEXT,                          -- "Documentation", "System", "Registration", "Filing"

    -- Status tracking
    status              TEXT NOT NULL DEFAULT 'PENDING', -- "PENDING", "IN_PROGRESS", "DONE", "SKIPPED", "ESCALATED"
    priority            TEXT NOT NULL DEFAULT 'MEDIUM',
    urgency             TEXT NOT NULL DEFAULT 'THIS_MONTH', -- "IMMEDIATE", "THIS_WEEK", "THIS_MONTH", "THIS_QUARTER", "THIS_YEAR", "ONGOING"

    -- Deadlines
    due_date            TEXT,
    completed_at        TEXT,
    completed_by        TEXT,                          -- "user", "agent", "ca_team"

    -- Escalation
    needs_human_approval INTEGER DEFAULT 0,
    recommended_approver TEXT,
    escalated_at        TEXT,
    escalation_reason   TEXT,

    -- Context
    estimated_effort_hours REAL DEFAULT 1.0,
    external_link       TEXT,                          -- Link to government portal
    notes               TEXT,

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (obligation_id) REFERENCES obligations(id),
    FOREIGN KEY (business_id) REFERENCES businesses(id),
    CHECK (status IN ('PENDING', 'IN_PROGRESS', 'DONE', 'SKIPPED', 'ESCALATED')),
    CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW'))
);

CREATE INDEX IF NOT EXISTS idx_actions_business ON action_items(business_id, status);
CREATE INDEX IF NOT EXISTS idx_actions_obligation ON action_items(obligation_id);
CREATE INDEX IF NOT EXISTS idx_actions_due ON action_items(due_date, status);
CREATE INDEX IF NOT EXISTS idx_actions_urgency ON action_items(urgency, status);


-- ============================================================
-- TABLE 5: audit_log
-- IMMUTABLE — never UPDATE or DELETE rows here.
-- Every agent decision, every action, every state change.
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id            TEXT NOT NULL UNIQUE,          -- UUID for cross-referencing
    timestamp           TEXT NOT NULL DEFAULT (datetime('now')),

    -- What happened
    agent_name          TEXT NOT NULL,                 -- "ProfileGuardian", "Monitor", "Analyst", etc.
    action              TEXT NOT NULL,                 -- "profile_created", "threshold_triggered", etc.
    status              TEXT NOT NULL DEFAULT 'success', -- "success", "failure", "partial", "running"

    -- Context
    business_id         TEXT,
    session_id          TEXT,
    obligation_id       TEXT,
    threshold_id        TEXT,

    -- Data
    input_summary       TEXT,                          -- JSON summary of inputs
    output_summary      TEXT,                          -- JSON summary of outputs
    confidence          REAL,
    citations           TEXT DEFAULT '[]',             -- JSON array of citations used

    -- Error handling
    error_message       TEXT,
    retry_count         INTEGER DEFAULT 0,
    recovery_action     TEXT,                          -- What the agent did to recover

    -- Performance
    duration_ms         INTEGER,                       -- How long this action took

    notes               TEXT,

    CHECK (status IN ('success', 'failure', 'partial', 'running', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_audit_business ON audit_log(business_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_log(agent_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_log(status, timestamp);


-- ============================================================
-- TABLE 6: alerts
-- Every alert generated by the system.
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    id                  TEXT PRIMARY KEY,
    business_id         TEXT NOT NULL,
    obligation_id       TEXT,
    session_id          TEXT,

    -- Alert content
    alert_type          TEXT NOT NULL,                 -- "NEW_OBLIGATION", "DEADLINE_APPROACHING",
                                                       -- "THRESHOLD_CROSSED", "NEW_REGULATION",
                                                       -- "ANOMALY", "ESCALATION_NEEDED"
    title               TEXT NOT NULL,
    message             TEXT NOT NULL,
    severity            TEXT NOT NULL DEFAULT 'MEDIUM', -- "CRITICAL", "HIGH", "MEDIUM", "LOW"
    regulator           TEXT,

    -- Delivery
    channel             TEXT DEFAULT 'in_app',         -- "in_app", "email", "both"
    sent_at             TEXT,
    read_at             TEXT,
    is_read             INTEGER DEFAULT 0,
    is_dismissed        INTEGER DEFAULT 0,

    -- Action link
    action_url          TEXT,                          -- Deep link to relevant screen
    action_label        TEXT,                          -- "View Obligation", "Run Analysis", etc.

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (business_id) REFERENCES businesses(id),
    CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    CHECK (alert_type IN (
        'NEW_OBLIGATION', 'DEADLINE_APPROACHING', 'THRESHOLD_CROSSED',
        'NEW_REGULATION', 'ANOMALY', 'ESCALATION_NEEDED', 'ANALYSIS_COMPLETE',
        'REPORT_READY', 'RISK_SCORE_CHANGE'
    ))
);

CREATE INDEX IF NOT EXISTS idx_alerts_business ON alerts(business_id, is_read);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity, is_dismissed);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type, created_at);


-- ============================================================
-- TABLE 7: regulatory_docs
-- Metadata for every regulatory document ingested into ChromaDB.
-- ============================================================
CREATE TABLE IF NOT EXISTS regulatory_docs (
    id                  TEXT PRIMARY KEY,
    regulator           TEXT NOT NULL,
    doc_title           TEXT NOT NULL,
    doc_type            TEXT NOT NULL,                 -- "Circular", "Master Direction", "Notification", "Act"
    notification_number TEXT,                          -- e.g. "CBIC Notification 17/2022-CT"
    effective_date      TEXT NOT NULL,
    published_date      TEXT,
    source_url          TEXT,
    local_file_path     TEXT,

    -- Ingestion status
    is_ingested         INTEGER DEFAULT 0,             -- 1 = chunks in ChromaDB
    chunk_count         INTEGER DEFAULT 0,
    ingested_at         TEXT,

    -- Content summary
    summary             TEXT,                          -- LLM-generated 2-3 sentence summary
    key_thresholds      TEXT DEFAULT '[]',             -- JSON: extracted threshold values
    affected_entities   TEXT DEFAULT '[]',             -- JSON: which entity types are affected
    is_threshold_change INTEGER DEFAULT 0,             -- 1 = this doc changes a threshold

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),

    CHECK (regulator IN ('GST', 'RBI', 'SEBI', 'MSME', 'MCA', 'IT', 'OTHER')),
    CHECK (doc_type IN ('Circular', 'Master Direction', 'Notification', 'Act', 'Amendment', 'Press Release'))
);

CREATE INDEX IF NOT EXISTS idx_regdocs_regulator ON regulatory_docs(regulator, effective_date);
CREATE INDEX IF NOT EXISTS idx_regdocs_ingested ON regulatory_docs(is_ingested);


-- ============================================================
-- TABLE 8: analysis_sessions
-- Groups all outputs from a single analysis run.
-- Makes it easy to show history: "You ran 3 analyses — here are the results"
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id                  TEXT PRIMARY KEY,              -- UUID
    business_id         TEXT NOT NULL,
    business_version    INTEGER NOT NULL,

    -- Results summary
    risk_score          INTEGER,                       -- 0-100
    risk_level          TEXT,                          -- "HIGH", "MEDIUM", "LOW"
    total_obligations   INTEGER DEFAULT 0,
    high_priority_count INTEGER DEFAULT 0,
    total_penalty_inr   REAL DEFAULT 0,
    total_actions       INTEGER DEFAULT 0,

    -- Agent pipeline status
    monitor_status      TEXT DEFAULT 'pending',
    analyst_status      TEXT DEFAULT 'pending',
    action_status       TEXT DEFAULT 'pending',
    simulation_status   TEXT DEFAULT 'skipped',

    -- Scenario (if simulation was run)
    is_scenario         INTEGER DEFAULT 0,
    scenario_turnover_cr REAL,
    scenario_description TEXT,
    new_obligations_count INTEGER DEFAULT 0,
    additional_penalty_inr REAL DEFAULT 0,

    -- Timing
    started_at          TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at        TEXT,
    duration_seconds    REAL,

    -- Report
    report_path         TEXT,                          -- Path to generated PDF/HTML report
    report_generated_at TEXT,

    FOREIGN KEY (business_id) REFERENCES businesses(id),
    CHECK (risk_level IN ('HIGH', 'MEDIUM', 'LOW', NULL))
);

CREATE INDEX IF NOT EXISTS idx_sessions_business ON analysis_sessions(business_id, started_at);


-- ============================================================
-- TABLE 9: risk_scores
-- Time-series of risk scores — lets us show "your risk over time"
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id         TEXT NOT NULL,
    session_id          TEXT NOT NULL,
    recorded_at         TEXT NOT NULL DEFAULT (datetime('now')),
    overall_score       INTEGER NOT NULL,
    risk_level          TEXT NOT NULL,
    gst_score           INTEGER DEFAULT 0,
    rbi_score           INTEGER DEFAULT 0,
    sebi_score          INTEGER DEFAULT 0,
    msme_score          INTEGER DEFAULT 0,
    penalty_exposure_inr REAL DEFAULT 0,
    obligation_count    INTEGER DEFAULT 0,

    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE INDEX IF NOT EXISTS idx_riskscores_business ON risk_scores(business_id, recorded_at);


-- ============================================================
-- TABLE 10: scheduled_jobs
-- Tracks APScheduler jobs — monitor knows what it last checked.
-- ============================================================
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id                  TEXT PRIMARY KEY,
    job_name            TEXT NOT NULL UNIQUE,          -- "daily_monitor", "weekly_report", etc.
    last_run_at         TEXT,
    last_run_status     TEXT,                          -- "success", "failure", "running"
    next_run_at         TEXT,
    run_count           INTEGER DEFAULT 0,
    failure_count       INTEGER DEFAULT 0,
    last_error          TEXT,
    is_enabled          INTEGER DEFAULT 1,

    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);