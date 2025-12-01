-- جدول المستخدمين (الباحثين)
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ar       TEXT    NOT NULL,
    name_en       TEXT,
    email         TEXT    NOT NULL UNIQUE,
    national_id   TEXT    UNIQUE,
    sector        TEXT,
    org_unit      TEXT,
    rank_title    TEXT,
    phone         TEXT,
    password_hash TEXT    NOT NULL,
    avatar_file   TEXT
);

-- جدول عناصر البحث / المشاريع (موجود عندك تقريبًا، تأكدي أو عدليه)
CREATE TABLE IF NOT EXISTS research_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    short           TEXT,
    abstract        TEXT,
    kind            TEXT, -- Research / Project / Innovation...
    year            INTEGER,
    field           TEXT,
    sector          TEXT,
    confidentiality TEXT,
    publisher       TEXT,
    link_url        TEXT,
    file_name       TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول الباحثين المرتبطين بكل بحث
CREATE TABLE IF NOT EXISTS authors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    research_id INTEGER NOT NULL,
    user_id     INTEGER,      -- لو موجود حساب في users يتم الربط
    name_ar     TEXT,
    name_en     TEXT,
    rank_title  TEXT,
    sector      TEXT,
    org_unit    TEXT,
    email       TEXT,
    phone       TEXT,
    gender      TEXT,
    avatar_file TEXT,
    is_main     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (research_id) REFERENCES research_items(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- جدول الإحصائيات (تستخدمينه في about)
CREATE TABLE IF NOT EXISTS metrics (
    key   TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
