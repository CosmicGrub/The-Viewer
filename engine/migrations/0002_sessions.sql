-- THE VIEWER -- schema migration 0002 (onboarding + parts request)
-- Backwards-compatibility rule R1: additive only. Adds new tables; nothing existing
-- is changed, so older code keeps working and this is rollbackable (drop these tables).

CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY,
    mechanic       TEXT,
    bumper_number  TEXT,            -- admin / "bumper" number
    tm             TEXT,
    uoc            TEXT,
    tech_status    TEXT,
    motor_sergeant TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_sessions_bumper ON sessions(bumper_number);

CREATE TABLE IF NOT EXISTS faults (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    description TEXT,                -- damage / work needed on the vehicle
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS request_items (
    id                 INTEGER PRIMARY KEY,
    session_id         INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    item_name          TEXT,
    nsn                TEXT,
    qty                TEXT,
    fig_no             TEXT,
    part_no            TEXT,
    unit_price         TEXT,         -- FEDLOG (manual for now)
    aac                TEXT,         -- FEDLOG
    arc                TEXT,         -- FEDLOG
    source_document_id INTEGER REFERENCES documents(id),
    source_page        INTEGER,
    created_at         TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_request_items_session ON request_items(session_id);
