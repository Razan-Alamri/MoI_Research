import os
import sqlite3
import re
from collections import defaultdict
from functools import wraps
import uuid
import json
from flask import (
    Flask, g, render_template, request,
    redirect, url_for, flash, send_from_directory,
    session
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import os, sqlite3
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, g, render_template, request, redirect, url_for,
    flash, session, abort
)

app = Flask(__name__)
app.secret_key = "moi-research"   # 

# إعداد مجلدات الرفع
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
UPLOAD_RESEARCH = os.path.join(UPLOAD_ROOT, "research")
UPLOAD_AVATARS = os.path.join(UPLOAD_ROOT, "avatars")
UPLOAD_INNOVATIONS = os.path.join(UPLOAD_ROOT, "innovations")
os.makedirs(UPLOAD_INNOVATIONS, exist_ok=True)

os.makedirs(UPLOAD_RESEARCH, exist_ok=True)
os.makedirs(UPLOAD_AVATARS, exist_ok=True)

ALLOWED_DOC_EXT = {"pdf", "doc", "docx", "ppt", "pptx"}
ALLOWED_IMG_EXT = {"jpg", "jpeg", "png", "gif", "webp", "avif"}

DATABASE = os.path.join(BASE_DIR, "data.db")


# ===================== DB Helpers =====================

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def allowed_file(filename, allowed_ext):
    if not filename:
        return False
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in allowed_ext



def save_uploaded_file(file_storage, upload_dir, allowed_ext):
    """
    يرجّع اسم الملف المحفوظ (مع الحفاظ على الامتداد) أو None لو ما فيه رفع / امتداد غير مسموح.
    """
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename, allowed_ext):
        return None

    filename = secure_filename(file_storage.filename)

    # لو تبغين نفس الاسم تمامًا بدون أي تغيير (مع خطر استبدال الملفات) استخدمي هذا:
    # final_name = filename

    # أو: نضيف prefix صغير عشان نضمن عدم التكرار + نحافظ على الاسم والامتداد
    unique = uuid.uuid4().hex[:8]
    final_name = f"{unique}_{filename}"

    full_path = os.path.join(upload_dir, final_name)
    file_storage.save(full_path)
    return final_name



def get_metric(key, default=0):
    db = get_db()
    cur = db.execute("SELECT value FROM metrics WHERE key = ?", (key,))
    row = cur.fetchone()
    return row["value"] if row else default


def increment_metric(key, step=1):
    db = get_db()
    db.execute(
        """
        INSERT INTO metrics (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = value + ?
        """,
        (key, step, step),
    )
    db.commit()
    
def table_exists(db, name: str) -> bool:
    r = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(r)

def column_exists(db, table: str, col: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == col for r in rows)

def ensure_admin_schema():
    db = get_db()

    # ====== Admin users (منفصل عن users حق الباحثين) ======
    db.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        name_ar TEXT,
        email TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',   -- admin / reviewer / innovation / partnerships / platform / viewer
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_login_at TEXT
    )
    """)

    # ====== Innovations (ابتكارات الزوار) ======
    db.execute("""
    CREATE TABLE IF NOT EXISTS innovations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL DEFAULT 'visitor',  -- visitor / internal
        name TEXT,
        email TEXT,
        phone_e164 TEXT,
        nationality TEXT,
        category TEXT,
        idea TEXT NOT NULL,
        attachment TEXT,
        status TEXT NOT NULL DEFAULT 'new',      -- new / triage / evaluating / poc / adopted / closed / rejected
        priority TEXT NOT NULL DEFAULT 'normal', -- low / normal / high
        assigned_to INTEGER,                     -- admin_users.id
        tags TEXT,                               -- CSV
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (assigned_to) REFERENCES admin_users(id)
    )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_innovations_status ON innovations(status)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_innovations_created ON innovations(created_at)")

    # ====== Content moderation queue (اعتماد محتوى الأبحاث/المشاريع) ======
    # نضيف أعمدة بسيطة لـ research_items إذا ما كانت موجودة
    # (SQLite ما يدعم IF NOT EXISTS في ALTER COLUMN، فنستخدم try/except)
    try:
        db.execute("ALTER TABLE research_items ADD COLUMN workflow_status TEXT DEFAULT 'published'")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE research_items ADD COLUMN workflow_notes TEXT")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE research_items ADD COLUMN reviewed_by INTEGER")
    except Exception:
        pass
    try:
        db.execute("ALTER TABLE research_items ADD COLUMN reviewed_at TEXT")
    except Exception:
        pass

    # workflow_status: draft / submitted / under_review / changes_requested / approved / rejected / published

    # ====== Partner requests (طلبات تعاون/دعم/تبنّي) ======
    db.execute("""
    CREATE TABLE IF NOT EXISTS partner_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_name TEXT,
        contact_name TEXT,
        email TEXT,
        phone_e164 TEXT,
        request_type TEXT NOT NULL,  -- support / adoption / partnership / funding
        topic TEXT,
        details TEXT NOT NULL,
        attachment TEXT,
        status TEXT NOT NULL DEFAULT 'new', -- new / in_review / approved / rejected / closed
        assigned_to INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (assigned_to) REFERENCES admin_users(id)
    )
    """)

    # ====== Taxonomy (تصنيفات/قواميس) ======
    db.execute("""
    CREATE TABLE IF NOT EXISTS taxonomy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,          -- sector / field / tag / confidentiality / year_bucket
        key TEXT NOT NULL,
        label_ar TEXT NOT NULL,
        label_en TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 0,
        UNIQUE(type, key)
    )
    """)

    # ====== KPI definitions + snapshots ======
    db.execute("""
    CREATE TABLE IF NOT EXISTS kpi_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,          -- e.g. total_research, total_projects ...
        title_ar TEXT NOT NULL,
        title_en TEXT,
        description TEXT,
        source_query TEXT,                 -- اختياري: تعريف مصدره
        is_active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """)
    db.execute("""
    CREATE TABLE IF NOT EXISTS kpi_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kpi_key TEXT NOT NULL,
        value REAL NOT NULL,
        snapshot_date TEXT NOT NULL DEFAULT (date('now')),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ====== Audit Log (سجل تدقيق) ======
    db.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_type TEXT NOT NULL,        -- admin / researcher / system
        actor_id INTEGER,
        action TEXT NOT NULL,            -- LOGIN / UPDATE_STATUS / APPROVE_CONTENT ...
        entity_type TEXT NOT NULL,       -- innovation / research_item / partner_request / taxonomy / kpi
        entity_id INTEGER,
        details TEXT,
        ip TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """)

    # ====== Seed admin إذا ما فيه ======
    cur = db.execute("SELECT COUNT(*) as c FROM admin_users")
    if cur.fetchone()["c"] == 0:
        # user: admin / pass: Admin@123 (غيريها فوراً بعد التشغيل)
        from werkzeug.security import generate_password_hash
        db.execute("""
        INSERT INTO admin_users (username, name_ar, email, password_hash, role)
        VALUES (?, ?, ?, ?, ?)
        """, ("admin", "مدير المنصة", "admin@moi.local", generate_password_hash("Admin@123"), "admin"))

        db.execute("""
        INSERT INTO kpi_definitions (key, title_ar, description, sort_order)
        VALUES
          ('kpi_total_research', 'إجمالي الأبحاث', 'عدد الأبحاث المعتمدة/المنشورة', 1),
          ('kpi_total_projects', 'إجمالي المشاريع', 'عدد المشاريع/النماذج الأولية', 2),
          ('kpi_innov_new', 'ابتكارات جديدة', 'عدد الابتكارات الواردة حديثًا', 3),
          ('kpi_pending_content', 'محتوى بانتظار الاعتماد', 'عناصر محتوى ضمن مسار المراجعة', 4)
        """)

    db.commit()

def _table_has_column(table_name: str, col_name: str) -> bool:
    db = get_db()
    cols = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(c["name"] == col_name for c in cols)

def migrate_audit_log():
    db = get_db()

    # لو الجدول غير موجود أصلاً لا تسوي شيء (ensure_admin_schema ينشئه)
    row = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='audit_log'
    """).fetchone()
    if not row:
        return

    # أضف الأعمدة الناقصة (SQLite يسمح بـ ADD COLUMN)
    if not _table_has_column("audit_log", "actor_type"):
        db.execute("ALTER TABLE audit_log ADD COLUMN actor_type TEXT NOT NULL DEFAULT 'admin'")
    if not _table_has_column("audit_log", "actor_id"):
        db.execute("ALTER TABLE audit_log ADD COLUMN actor_id INTEGER")
    if not _table_has_column("audit_log", "ip"):
        db.execute("ALTER TABLE audit_log ADD COLUMN ip TEXT")
    if not _table_has_column("audit_log", "details"):
        # بعض النسخ القديمة ما فيها details
        db.execute("ALTER TABLE audit_log ADD COLUMN details TEXT")
    if not _table_has_column("audit_log", "entity_id"):
        # بعض النسخ القديمة ما فيها entity_id
        db.execute("ALTER TABLE audit_log ADD COLUMN entity_id INTEGER")

    db.commit()
def table_exists(table_name: str) -> bool:
    db = get_db()
    row = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,)).fetchone()
    return bool(row)

def column_exists(table_name: str, col_name: str) -> bool:
    db = get_db()
    cols = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(c["name"] == col_name for c in cols)

def migrate_innovations():
    db = get_db()
    if not table_exists("innovations"):
        return

    # أعمدة تحتاجينها من الفورم/الأدمن
    if not column_exists("innovations", "nationality"):
        db.execute("ALTER TABLE innovations ADD COLUMN nationality TEXT")

    if not column_exists("innovations", "sector"):
        db.execute("ALTER TABLE innovations ADD COLUMN sector TEXT")

    if not column_exists("innovations", "source"):
        db.execute("ALTER TABLE innovations ADD COLUMN source TEXT NOT NULL DEFAULT 'visitor'")

    if not column_exists("innovations", "assigned_to"):
        db.execute("ALTER TABLE innovations ADD COLUMN assigned_to INTEGER")

    if not column_exists("innovations", "priority"):
        db.execute("ALTER TABLE innovations ADD COLUMN priority TEXT NOT NULL DEFAULT 'normal'")

    if not column_exists("innovations", "review_notes"):
        db.execute("ALTER TABLE innovations ADD COLUMN review_notes TEXT")

    # updated_at موجود عندك، بس نخليه يحدث منطقيًا من الكود
    db.commit()

# ===================== Admin Auth Helpers =====================

def get_current_admin():
    admin_id = session.get("admin_id")
    if not admin_id:
        return None
    db = get_db()
    return db.execute("SELECT * FROM admin_users WHERE id = ? AND is_active = 1", (admin_id,)).fetchone()

def admin_login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            flash("يجب تسجيل الدخول للوصول إلى لوحة الإدارة.", "login_required")
            return redirect(url_for("admin_login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped

def log_audit(action, entity_type, entity_id=None, details=None, actor_type="system", actor_id=None):
    db = get_db()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    # نخلي details نص JSON أو نص عادي
    details_text = None
    if details is not None:
        if isinstance(details, (dict, list)):
            details_text = json.dumps(details, ensure_ascii=False)
        else:
            details_text = str(details)

    db.execute("""
        INSERT INTO audit_log
        (actor_type, actor_id, action, entity_type, entity_id, details, ip, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (actor_type, actor_id, action, entity_type, entity_id, details_text, ip))
    db.commit()

# ===================== بوابة الادارة =====================
# ===================== Admin Routes =====================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    db = get_db()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        admin = db.execute("""
            SELECT * FROM admin_users
            WHERE username = ? AND is_active = 1
            LIMIT 1
        """, (username,)).fetchone()

        if not admin or not check_password_hash(admin["password_hash"], password):
            flash("بيانات الدخول غير صحيحة.", "error")
            return redirect(request.url)

        session["admin_id"] = admin["id"]
        db.execute("UPDATE admin_users SET last_login_at = datetime('now') WHERE id = ?", (admin["id"],))
        db.commit()

        log_audit("admin_login", "admin_users", admin["id"], {"username": username}, actor_type="admin", actor_id=admin["id"])

        next_url = request.args.get("next")
        return redirect(next_url or url_for("admin_dashboard"))

    return render_template("admin/admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    admin = get_current_admin()
    if admin:
        log_audit("admin_logout", "admin_users", admin["id"], None, actor_type="admin", actor_id=admin["id"])
    session.pop("admin_id", None)
    flash("تم تسجيل الخروج.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_login_required
def admin_dashboard():
    db = get_db()
    admin = get_current_admin()

    stats = {}
    stats["innovations_new"] = db.execute("SELECT COUNT(*) c FROM innovations WHERE status='new'").fetchone()["c"]
    stats["innovations_in_review"] = db.execute("SELECT COUNT(*) c FROM innovations WHERE status='in_review'").fetchone()["c"]
    stats["partner_new"] = db.execute("SELECT COUNT(*) c FROM partner_requests WHERE status='new'").fetchone()["c"]
    stats["content_pending"] = db.execute("SELECT COUNT(*) c FROM research_items WHERE workflow_status='pending'").fetchone()["c"]

    inv_by_status = db.execute("SELECT status, COUNT(*) c FROM innovations GROUP BY status").fetchall()
    content_by_status = db.execute("SELECT workflow_status AS status, COUNT(*) c FROM research_items GROUP BY workflow_status").fetchall()
    pr_by_status = db.execute("SELECT status, COUNT(*) c FROM partner_requests GROUP BY status").fetchall()

    # ✅ مهم جداً: تحويل Rows إلى dicts
    inv_by_status = [dict(r) for r in inv_by_status]
    content_by_status = [dict(r) for r in content_by_status]
    pr_by_status = [dict(r) for r in pr_by_status]

    audit8 = db.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 8").fetchall()

    return render_template(
        "admin/admin_dashboard.html",
        admin=admin,
        stats=stats,
        inv_by_status=inv_by_status,
        content_by_status=content_by_status,
        pr_by_status=pr_by_status,
        audit8=audit8
    )

# ---------- الابتكارات ----------
@app.route("/admin/innovations")
@admin_login_required
def admin_innovations():
    db = get_db()
    admin = get_current_admin()

    status   = request.args.get("status","").strip()
    source   = request.args.get("source","").strip()
    priority = request.args.get("priority","").strip()
    category = request.args.get("category","").strip()
    q        = request.args.get("q","").strip()

    where = []
    params = []

    if status:
        where.append("i.status = ?")
        params.append(status)

    if source:
        where.append("i.source = ?")
        params.append(source)

    if priority:
        where.append("i.priority = ?")
        params.append(priority)

    if category:
        where.append("i.category = ?")
        params.append(category)

    if q:
        like = f"%{q}%"
        where.append("(i.email LIKE ? OR i.name LIKE ? OR i.idea LIKE ? OR i.category LIKE ?)")
        params.extend([like, like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = db.execute(f"""
        SELECT i.*, a.name_ar AS assigned_name
        FROM innovations i
        LEFT JOIN admin_users a ON a.id = i.assigned_to
        {where_sql}
        ORDER BY i.created_at DESC
    """, params).fetchall()

    # التصنيفات
    categories = [r["category"] for r in db.execute("""
        SELECT DISTINCT category FROM innovations
        WHERE category IS NOT NULL AND category <> ''
        ORDER BY category ASC
    """).fetchall()]

    # KPIs
    kpi_rows = db.execute("""
      SELECT
        SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) AS c_new,
        SUM(CASE WHEN status='in_review' THEN 1 ELSE 0 END) AS c_in_review,
        SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS c_done,
        COUNT(*) AS c_total
      FROM innovations
    """).fetchone()

    kpis = {
      "total": kpi_rows["c_total"] or 0,
      "new": kpi_rows["c_new"] or 0,
      "in_review": kpi_rows["c_in_review"] or 0,
      "done": kpi_rows["c_done"] or 0,
    }

    # تحويلات عربي + بادج
    status_ar = {
      "new": "جديد",
      "in_review": "قيد المراجعة",
      "assigned": "مُسند",
      "done": "مكتمل",
      "rejected": "مرفوض",
    }
    source_ar = {"visitor":"زائر","researcher":"باحث","admin":"إدارة"}
    priority_ar = {"low":"منخفضة","normal":"عادية","high":"عالية","urgent":"عاجلة"}

    def status_badge(s):
      if s == "done": return "badge-success"
      if s == "new": return "badge-warn"
      if s == "rejected": return "badge-danger"
      return "badge-info"

    def priority_badge(p):
      if p == "urgent": return "badge-danger"
      if p == "high": return "badge-warn"
      if p == "low": return "badge-info"
      return ""

    innovations = []
    for r in rows:
      d = dict(r)
      d["status_ar"] = status_ar.get(d.get("status"), "—")
      d["source_ar"] = source_ar.get(d.get("source"), "—")
      d["priority_ar"] = priority_ar.get(d.get("priority"), "—")
      d["status_badge"] = status_badge(d.get("status"))
      d["priority_badge"] = priority_badge(d.get("priority"))
      innovations.append(d)

    return render_template(
      "admin/admin_innovations.html",
      admin=admin,
      innovations=innovations,
      categories=categories,
      kpis=kpis
    )


@app.route("/admin/innovations/<int:inv_id>", methods=["GET", "POST"])
@admin_login_required
def admin_innovation_view(inv_id):
    db = get_db()
    admin = get_current_admin()

    inv = db.execute("SELECT * FROM innovations WHERE id = ?", (inv_id,)).fetchone()
    if not inv:
        flash("الابتكار غير موجود.", "error")
        return redirect(url_for("admin_innovations"))

    admins = db.execute("SELECT id, name_ar, username FROM admin_users WHERE is_active=1 ORDER BY name_ar").fetchall()

    if request.method == "POST":
        status = request.form.get("status", inv["status"])
        priority = request.form.get("priority", inv["priority"])
        assigned_to = request.form.get("assigned_to", "") or None
        review_notes = request.form.get("review_notes", "").strip()

        db.execute("""
            UPDATE innovations
            SET status=?, priority=?, assigned_to=?, review_notes=?, updated_at=datetime('now')
            WHERE id=?
        """, (status, priority, assigned_to, review_notes, inv_id))
        db.commit()

        log_audit(
            "innovation_update",
            "innovations",
            inv_id,
            {"status": status, "priority": priority, "assigned_to": assigned_to},
            actor_type="admin",
            actor_id=admin["id"]
        )

        flash("تم تحديث الابتكار.", "success")
        return redirect(url_for("admin_innovation_view", inv_id=inv_id))

    return render_template("admin/admin_innovation_view.html", admin=admin, inv=inv, admins=admins)

@app.route("/admin/innovations/<int:inv_id>/update", methods=["POST"])
@admin_login_required
def admin_innovation_update(inv_id):
    db = get_db()
    admin = get_current_admin()

    status      = (request.form.get("status") or "").strip()
    priority    = (request.form.get("priority") or "").strip()
    assigned_to = request.form.get("assigned_to")
    review_notes = request.form.get("review_notes") or None

    # تنظيف assigned_to
    if assigned_to in ("", None):
        assigned_to = None
    else:
        try:
            assigned_to = int(assigned_to)
        except:
            assigned_to = None

    # (اختياري) تحقق من القيم المسموحة
    allowed_status = {"new","in_review","assigned","done","rejected"}
    allowed_priority = {"low","normal","high","urgent"}

    updates = []
    params = []

    if status and status in allowed_status:
        updates.append("status=?")
        params.append(status)

    if priority and priority in allowed_priority:
        updates.append("priority=?")
        params.append(priority)

    updates.append("assigned_to=?")
    params.append(assigned_to)

    updates.append("review_notes=?")
    params.append(review_notes)

    updates.append("updated_at=datetime('now')")

    if not updates:
        flash("لا توجد تغييرات للحفظ.", "error")
        return redirect(url_for("admin_innovation_view", inv_id=inv_id))

    params.append(inv_id)

    db.execute(f"""
        UPDATE innovations
        SET {", ".join(updates)}
        WHERE id=?
    """, params)
    db.commit()

    # سجل التدقيق
    # تأكدي أن log_audit عندك يقبل التفاصيل كنص
    log_audit("تحديث ابتكار", "innovations", inv_id, details="تعديل حالة/أولوية/إسناد/ملاحظات", actor_id=admin["id"])
    flash("تم تحديث الابتكار بنجاح.", "success")
    return redirect(url_for("admin_innovation_view", inv_id=inv_id))


# ---------- اعتماد المحتوى ----------
WORKFLOW_LABELS = {
    "pending": "معلّق",
    "published": "منشور",
    "needs_changes": "بحاجة لتعديلات",
    "rejected": "مرفوض",
}

@app.route("/admin/content")
@admin_login_required
def admin_content():
    db = get_db()
    admin = get_current_admin()

    status = request.args.get("status","").strip()
    sector = request.args.get("sector","").strip()
    q = request.args.get("q","").strip()

    where = []
    params = []

    if status:
        where.append("r.workflow_status = ?")
        params.append(status)

    if sector:
        where.append("r.sector = ?")
        params.append(sector)

    if q:
        like = f"%{q}%"
        where.append("(r.title LIKE ? OR r.kind LIKE ? OR r.field LIKE ? OR r.publisher LIKE ?)")
        params.extend([like, like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = db.execute(f"""
        SELECT r.*
        FROM research_items r
        {where_sql}
        ORDER BY r.created_at DESC
    """, params).fetchall()

    # القطاعات بالعربي
    sectors = db.execute("""
        SELECT key, label_ar
        FROM taxonomy
        WHERE type='sector' AND is_active=1
        ORDER BY sort_order, label_ar
    """).fetchall()

    # KPIs حسب الفلاتر
    kpi_rows = db.execute(f"""
        SELECT workflow_status AS status, COUNT(*) AS c
        FROM research_items r
        {where_sql}
        GROUP BY workflow_status
    """, params).fetchall()

    kpis = {"total": len(rows), "pending": 0, "published": 0, "needs_changes": 0, "rejected": 0}
    for x in kpi_rows:
        kpis[x["status"]] = x["c"]

    return render_template(
        "admin/admin_content.html",
        admin=admin,
        rows=rows,
        sectors=sectors,
        kpis=kpis,
        status=status,
        sector=sector,
        q=q,
        labels=WORKFLOW_LABELS
    )

@app.route("/admin/content/<int:item_id>", methods=["GET", "POST"])
@admin_login_required
def admin_content_view(item_id):
    db = get_db()
    admin = get_current_admin()

    item = db.execute("SELECT * FROM research_items WHERE id=?", (item_id,)).fetchone()
    if not item:
        flash("العنصر غير موجود.", "error")
        return redirect(url_for("admin_content"))

    if request.method == "POST":
        new_status = request.form.get("workflow_status", item["workflow_status"])
        notes = request.form.get("workflow_notes", "").strip()

        db.execute("""
            UPDATE research_items
            SET workflow_status=?, workflow_notes=?, reviewed_by=?, reviewed_at=datetime('now')
            WHERE id=?
        """, (new_status, notes, admin["id"], item_id))
        db.commit()

        log_audit("content_workflow_update", "research_items", item_id,
                  {"workflow_status": new_status}, actor_type="admin", actor_id=admin["id"])

        flash("تم تحديث حالة الاعتماد.", "success")
        return redirect(url_for("admin_content_view", item_id=item_id))

    return render_template("admin/admin_content_view.html", admin=admin, item=item)


# ---------- إدارة الباحثين ----------
@app.route("/admin/researchers")
@admin_login_required
def admin_researchers():
    db = get_db()
    admin = get_current_admin()

    sector = request.args.get("sector", "").strip()
    q = request.args.get("q", "").strip()

    where = []
    params = []

    if sector:
        where.append("u.sector = ?")
        params.append(sector)

    if q:
        like = f"%{q}%"
        where.append("(u.name_ar LIKE ? OR u.email LIKE ?)")
        params.extend([like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    # taxonomy sectors (Arabic labels)
    sectors = db.execute("""
      SELECT key, label_ar
      FROM taxonomy
      WHERE type='sector' AND is_active=1
      ORDER BY sort_order ASC, label_ar ASC
    """).fetchall()

    # researchers list + counts (research_items assumed linked by email in publisher OR authors table if you have it)
    # ✅ هنا ربطنا بالأفضل (authors.user_id) لأن عندك جدول authors وفيه user_id
    users = db.execute(f"""
      SELECT
        u.*,
        COALESCE(t.label_ar, '—') AS sector_ar,
        -- إجمالي العناصر التي شارك فيها كباحث
        (SELECT COUNT(DISTINCT a.research_id)
         FROM authors a
         WHERE a.user_id = u.id) AS total_items,

        -- منشور
        (SELECT COUNT(DISTINCT a.research_id)
         FROM authors a
         JOIN research_items r ON r.id = a.research_id
         WHERE a.user_id = u.id AND r.workflow_status='published') AS published_items,

        -- معلّق
        (SELECT COUNT(DISTINCT a.research_id)
         FROM authors a
         JOIN research_items r ON r.id = a.research_id
         WHERE a.user_id = u.id AND r.workflow_status='pending') AS pending_items

      FROM users u
      LEFT JOIN taxonomy t ON t.type='sector' AND t.key = u.sector
      {where_sql}
      ORDER BY u.id DESC
    """, params).fetchall()

    # KPIs
    k_total_users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] or 0
    k_with_content = db.execute("""
      SELECT COUNT(*) c
      FROM users u
      WHERE EXISTS (SELECT 1 FROM authors a WHERE a.user_id=u.id)
    """).fetchone()["c"] or 0

    top_sector = db.execute("""
      SELECT COALESCE(t.label_ar,'—') AS sector_name, COUNT(DISTINCT a.research_id) c
      FROM authors a
      JOIN users u ON u.id=a.user_id
      LEFT JOIN taxonomy t ON t.type='sector' AND t.key=u.sector
      GROUP BY sector_name
      ORDER BY c DESC
      LIMIT 1
    """).fetchone()

    total_published = db.execute("""
      SELECT COUNT(*) c
      FROM research_items
      WHERE workflow_status='published'
    """).fetchone()["c"] or 0

    kpis = {
        "total_users": k_total_users,
        "with_content": k_with_content,
        "top_sector_name": (top_sector["sector_name"] if top_sector else "—"),
        "total_published": total_published,
    }

    return render_template(
        "admin/admin_researchers.html",
        admin=admin,
        users=users,
        sectors=sectors,
        kpis=kpis
    )


@app.route("/admin/researchers/<int:user_id>")
@admin_login_required
def admin_researcher_view(user_id):
    db = get_db()
    admin = get_current_admin()

    u = db.execute("""
      SELECT u.*, COALESCE(t.label_ar,'—') AS sector_ar
      FROM users u
      LEFT JOIN taxonomy t ON t.type='sector' AND t.key=u.sector
      WHERE u.id=?
    """, (user_id,)).fetchone()

    if not u:
        flash("الباحث غير موجود.", "error")
        return redirect(url_for("admin_researchers"))

    # KPIs للباحث
    k = db.execute("""
      SELECT
        SUM(CASE WHEN r.workflow_status='published' THEN 1 ELSE 0 END) AS published,
        SUM(CASE WHEN r.workflow_status='pending' THEN 1 ELSE 0 END) AS pending,
        SUM(CASE WHEN r.workflow_status='needs_changes' THEN 1 ELSE 0 END) AS needs_changes,
        COUNT(*) AS total
      FROM authors a
      JOIN research_items r ON r.id=a.research_id
      WHERE a.user_id=?
    """, (user_id,)).fetchone()

    kpis = {
        "total": k["total"] or 0,
        "published": k["published"] or 0,
        "pending": k["pending"] or 0,
        "needs_changes": k["needs_changes"] or 0,
    }

    # آخر 20 عنصر
    items = db.execute("""
      SELECT r.*
      FROM authors a
      JOIN research_items r ON r.id=a.research_id
      WHERE a.user_id=?
      GROUP BY r.id
      ORDER BY r.created_at DESC
      LIMIT 20
    """, (user_id,)).fetchall()

    return render_template(
        "admin/admin_researcher_view.html",
        admin=admin,
        user=u,
        kpis=kpis,
        items=items
    )

# ---------- الشراكات ----------
PARTNER_STATUS_LABELS = {
    "new": "جديد",
    "in_review": "قيد المراجعة",
    "assigned": "مُسند",
    "done": "مكتمل",
    "rejected": "مرفوض",
}

@app.route("/admin/partners")
@admin_login_required
def admin_partners():
    db = get_db()
    admin = get_current_admin()

    status = request.args.get("status","").strip()
    q = request.args.get("q","").strip()

    where = []
    params = []

    if status:
        where.append("p.status = ?")
        params.append(status)

    if q:
        like = f"%{q}%"
        where.append("(p.org_name LIKE ? OR p.contact_name LIKE ? OR p.email LIKE ? OR p.topic LIKE ? OR p.details LIKE ?)")
        params.extend([like, like, like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = db.execute(f"""
        SELECT p.*, a.name_ar AS assigned_name
        FROM partner_requests p
        LEFT JOIN admin_users a ON a.id = p.assigned_to
        {where_sql}
        ORDER BY p.created_at DESC
    """, params).fetchall()

    kpi_rows = db.execute(f"""
        SELECT status, COUNT(*) AS c
        FROM partner_requests p
        {where_sql}
        GROUP BY status
    """, params).fetchall()

    kpis = {"total": len(rows), "new": 0, "in_review": 0, "assigned": 0, "done": 0, "rejected": 0}
    for x in kpi_rows:
        kpis[x["status"]] = x["c"]

    return render_template("admin/admin_partners.html",
        admin=admin, rows=rows, kpis=kpis, status=status, q=q, labels=PARTNER_STATUS_LABELS)


@app.route("/admin/partners/<int:req_id>", methods=["GET","POST"])
@admin_login_required
def admin_partner_view(req_id):
    db = get_db()
    admin = get_current_admin()

    req = db.execute("SELECT * FROM partner_requests WHERE id=?", (req_id,)).fetchone()
    if not req:
        flash("الطلب غير موجود.", "error")
        return redirect(url_for("admin_partners"))

    admins = db.execute("SELECT id, name_ar, username FROM admin_users WHERE is_active=1 ORDER BY name_ar").fetchall()

    if request.method == "POST":
        status = request.form.get("status", req["status"])
        assigned_to = request.form.get("assigned_to", "") or None

        db.execute("""
            UPDATE partner_requests
            SET status=?, assigned_to=?, updated_at=datetime('now')
            WHERE id=?
        """, (status, assigned_to, req_id))
        db.commit()

        log_audit("partner_request_update", "partner_requests", req_id,
                  {"status": status, "assigned_to": assigned_to},
                  actor_type="admin", actor_id=admin["id"])

        flash("تم تحديث الطلب.", "success")
        return redirect(url_for("admin_partner_view", req_id=req_id))

    return render_template("admin/admin_partner_view.html", admin=admin, req=req, admins=admins)


# ---------- إدارة المنصة: taxonomy + KPIs + Audit ----------
TAX_TYPES_AR = {
    "sector": "القطاعات",
    "field": "المجالات",
    "kind": "الأنواع",
    "confidentiality": "السرية",
}

@app.route("/admin/taxonomy", methods=["GET","POST"])
@admin_login_required
def admin_taxonomy():
    db = get_db()
    admin = get_current_admin()

    if request.method == "POST":
        ttype = request.form.get("type")
        key = (request.form.get("key") or "").strip()
        label_ar = (request.form.get("label_ar") or "").strip()
        label_en = None  # ما نستخدمها بالواجهة
        sort_order = int(request.form.get("sort_order") or 0)
        is_active = 1 if request.form.get("is_active") == "1" else 0

        if not (ttype and key and label_ar):
            flash("فضلاً أكمل الحقول المطلوبة.", "error")
            return redirect(url_for("admin_taxonomy", type=ttype or "sector"))

        db.execute("""
            INSERT OR REPLACE INTO taxonomy(type,key,label_ar,label_en,is_active,sort_order)
            VALUES(?,?,?,?,?,?)
        """, (ttype, key, label_ar, label_en, is_active, sort_order))
        db.commit()

        log_audit("تحديث تصنيف", "taxonomy", None, details=f"{ttype}:{key}", actor_id=admin["id"])
        flash("تم حفظ التصنيف.", "success")
        return redirect(url_for("admin_taxonomy", type=ttype))

    t = request.args.get("type", "sector")

    rows = db.execute("""
        SELECT * FROM taxonomy
        WHERE type=?
        ORDER BY sort_order ASC, label_ar ASC
    """, (t,)).fetchall()

    # KPIs
    k_total = db.execute("SELECT COUNT(*) c FROM taxonomy WHERE type=?", (t,)).fetchone()["c"]
    k_active = db.execute("SELECT COUNT(*) c FROM taxonomy WHERE type=? AND is_active=1", (t,)).fetchone()["c"]
    k_inactive = k_total - k_active

    return render_template("admin/taxonomy.html",
        admin=admin, rows=rows, t=t,
        types_ar=TAX_TYPES_AR,
        kpis={"total":k_total,"active":k_active,"inactive":k_inactive},
        title_ar=TAX_TYPES_AR.get(t, "التصنيفات")
    )


@app.route("/admin/audit")
@admin_login_required
def admin_audit():
    db = get_db()
    admin = get_current_admin()

    q = request.args.get("q","").strip()
    actor_type = request.args.get("actor_type","").strip()

    where = []
    params = []

    if actor_type:
        where.append("a.actor_type = ?")
        params.append(actor_type)

    if q:
        like = f"%{q}%"
        where.append("(a.action LIKE ? OR a.entity_type LIKE ? OR a.details LIKE ? OR a.ip LIKE ?)")
        params.extend([like, like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    rows = db.execute(f"""
        SELECT *
        FROM audit_log a
        {where_sql}
        ORDER BY a.created_at DESC
        LIMIT 250
    """, params).fetchall()

    k_total = db.execute("SELECT COUNT(*) c FROM audit_log").fetchone()["c"]

    return render_template("admin/admin_audit.html",
        admin=admin, rows=rows, kpis={"total":k_total, "shown":len(rows)}, q=q, actor_type=actor_type)

# ===================== صفحات عامة =====================

# صفحة الهبوط الرئيسية /
@app.route("/")
def landing():
    start_clicks = get_metric("start_clicks", 0)
    return render_template("landing.html", start_clicks=start_clicks)


# صفحة بوابة المنصة /portal
@app.route("/portal")
def index():
    return render_template("index.html")


# زر "ابدأ" في صفحة الهبوط
@app.route("/start")
def start():
    increment_metric("start_clicks", 1)
    return redirect(url_for("index"))


@app.route("/about")
def about():
    start_clicks = get_metric("start_clicks", 0)
    return render_template("about.html", start_clicks=start_clicks)


@app.route("/sector/<slug>")
def sector(slug):
    return render_template("sector.html", slug=slug)


@app.route("/detail/<int:item_id>")
def detail(item_id):
    db = get_db()

    cur = db.execute("SELECT * FROM research_items WHERE id = ?", (item_id,))
    row = cur.fetchone()

    item_db = dict(row) if row else None
    authors_db = []

    if item_db:
        cur_a = db.execute("""
            SELECT
                name_ar,
                name_en,
                rank_title,
                sector,
                org_unit,
                email,
                phone,
                gender,
                avatar_file
            FROM authors
            WHERE research_id = ?
        """, (item_id,))
        rows_a = cur_a.fetchall()

        for a in rows_a:
            name = a["name_ar"] or a["name_en"] or ""

            authors_db.append({
                "name": name,
                "rank": a["rank_title"] or "",
                "sector": a["sector"] or "",
                "unit": a["org_unit"] or "",
                "email": a["email"] or "",
                "phone": a["phone"] or "",
                "gender": a["gender"] or "",
                "avatar_file": a["avatar_file"] or ""
            })

    detail_source = "db" if item_db else "mock"

    return render_template(
        "detail.html",
        item_id=item_id,
        detail_source=detail_source,
        detail_item=item_db,
        detail_authors=authors_db,
    )


@app.route("/dashboard")
def dashboard():
    start_clicks = get_metric("start_clicks", 0)
    return render_template("dashboard.html", start_clicks=start_clicks)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = []

    if q:
        like = f"%{q}%"
        db = get_db()
        cur = db.execute("""
            SELECT
                r.id,
                r.title,
                r.short,
                r.abstract,
                r.kind AS type,          -- ✅ علشان يتطابق مع MOCK
                r.year,
                r.field,
                r.sector,
                r.confidentiality,
                r.publisher,
                r.link_url,
                r.file_name,
                r.created_at,
                COALESCE(GROUP_CONCAT(a.name_ar, '، '), '') AS authors_names
            FROM research_items r
            LEFT JOIN authors a
              ON a.research_id = r.id
            WHERE
                r.title    LIKE ?
                OR r.short LIKE ?
                OR r.abstract LIKE ?
                OR r.field  LIKE ?
                OR r.sector LIKE ?
            GROUP BY r.id
            ORDER BY r.year DESC, r.created_at DESC
        """, (like, like, like, like, like))

        rows = cur.fetchall()

        # ✅ أهم خطوة: نحول Row → dict عشان tojson ما يطيح
        results = [dict(row) for row in rows]

    return render_template("search.html", q=q, results=results)


@app.route("/submit_innovation", methods=["POST"])
def submit_innovation():
    db = get_db()

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    nationality = request.form.get("nationality", "").strip()
    sector = request.form.get("sector", "").strip()  # إذا بتضيفينه للفورم لاحقًا
    category = request.form.get("category", "").strip()
    idea = request.form.get("idea", "").strip()

    phone_display = request.form.get("phone_display", "").strip()
    phone_e164 = request.form.get("phone_e164", "").strip()


    source = "visitor"  # أو kiosk لو تبين تفرزين معرض الدفاع مثلاً

    file = request.files.get("attachment")
    filename = save_uploaded_file(file, UPLOAD_ROOT, ALLOWED_DOC_EXT)

    db.execute("""
        INSERT INTO innovations
        (name, email, nationality, sector, phone_display, phone_e164,
         category, idea, attachment, source, status, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', 'normal', datetime('now'), datetime('now'))
    """, (
        name, email, nationality, sector, phone_display, phone_e164,
        category, idea, filename, source
    ))

    db.commit()
    flash("تم استلام فكرتك بنجاح!", "success")
    return redirect(url_for("index"))


# ===================== بوابة الباحثين =====================
# ===================== Auth Helpers =====================

def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE id = ?", (uid,))
    return cur.fetchone()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            # غيّرنا التصنيف من "error" إلى "login_required"
            flash("يجب تسجيل الدخول للوصول إلى بوابة الباحثين.", "login_required")
            # نحفظ المسار اللي كان يبيه (اختياري)
            return redirect(url_for("researcher_login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped

# ===================== Auth Routes للباحثين =====================

# @app.route("/researcher/login", methods=["GET", "POST"])
# def researcher_login():
#     db = get_db()
#     if request.method == "POST":
#         username = request.form.get("username", "").strip()
#         password = request.form.get("password", "").strip()

#         if not username or not password:
#             flash("الرجاء إدخال بيانات الدخول.", "error")
#             return redirect(request.url)

#         # نسمح بالدخول بالبريد أو الهوية
#         cur = db.execute(
#             """
#             SELECT * FROM users
#             WHERE email = ? OR national_id = ?
#             LIMIT 1
#             """,
#             (username, username),
#         )
#         user = cur.fetchone()
#         if not user or not check_password_hash(user["password_hash"], password):
#             flash("بيانات الدخول غير صحيحة.", "error")
#             return redirect(request.url)

#         session["user_id"] = user["id"]
#         flash("تم تسجيل الدخول بنجاح.", "success")
#         return redirect(url_for("researcher_dashboard"))

#     return render_template("researcher_login.html")


@app.route("/researcher/login", methods=["GET", "POST"])
def researcher_login():
    db = get_db()

    if request.method == "POST":
        mode = request.form.get("mode", "login")

        # ================== إنشاء حساب جديد ==================
        if mode == "register":
            name_ar     = request.form.get("reg_name_ar", "").strip()
            name_en     = request.form.get("reg_name_en", "").strip()
            email       = request.form.get("reg_email", "").strip().lower()
            national_id = request.form.get("reg_national_id", "").strip()
            sector      = request.form.get("reg_sector", "").strip()
            org_unit    = request.form.get("reg_org_unit", "").strip()
            rank_title  = request.form.get("reg_rank_title", "").strip()
            phone       = request.form.get("reg_phone", "").strip()
            password    = request.form.get("reg_password", "").strip()
            password2   = request.form.get("reg_password2", "").strip()

            # ✅ تحقق من الحقول
            if not (name_ar and email and national_id and sector and org_unit and
                    rank_title and phone and password and password2):
                flash("جميع الحقول مطلوبة ما عدا الصورة الشخصية.", "error")
                return redirect(request.url)

            if password != password2:
                flash("كلمتا المرور غير متطابقتين.", "error")
                return redirect(request.url)

            # ✅ منع تكرار البريد/الهوية
            cur = db.execute(
                "SELECT id FROM users WHERE lower(email) = ? OR national_id = ?",
                (email, national_id),
            )
            if cur.fetchone():
                flash("يوجد حساب مسجل مسبقًا بنفس البريد الإلكتروني أو رقم الهوية.", "error")
                return redirect(request.url)

            # ✅ الصورة (اختيارية)
            avatar_storage = request.files.get("reg_avatar")
            avatar_file = None
            if avatar_storage and avatar_storage.filename:
                avatar_file = save_uploaded_file(
                    avatar_storage,
                    UPLOAD_AVATARS,
                    ALLOWED_IMG_EXT
                )

            # ❗️بدون هاش — نخزنها نص صريح
            password_hash = password

            db.execute(
                """
                INSERT INTO users
                  (name_ar, name_en, email, national_id,
                   sector, org_unit, rank_title, phone,
                   password_hash, avatar_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name_ar,
                    name_en,
                    email,   # lowercase
                    national_id,
                    sector,
                    org_unit,
                    rank_title,
                    phone,
                    password_hash,
                    avatar_file,
                ),
            )
            db.commit()

            user = db.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()

            session["user_id"] = user["id"]
            flash("تم إنشاء حسابك بنجاح، وتم تسجيل دخولك.", "success")
            return redirect(url_for("researcher_dashboard"))

        # ================== تسجيل الدخول ==================
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("الرجاء إدخال بيانات الدخول.", "error")
            return redirect(request.url)

        username_email = username.lower()

        cur = db.execute(
            """
            SELECT * FROM users
            WHERE lower(email) = ? OR national_id = ?
            LIMIT 1
            """,
            (username_email, username),
        )
        user = cur.fetchone()

        if not user:
            flash("لا يوجد حساب مطابق للبريد الإلكتروني أو رقم الهوية المدخل.", "error")
            return redirect(request.url)

        # ❗️بدون check_password_hash — مقارنة مباشرة
        if user["password_hash"] != password:
            flash("كلمة المرور غير صحيحة. الرجاء المحاولة مرة أخرى.", "error")
            return redirect(request.url)

        # ✅ نجاح تسجيل الدخول
        session["user_id"] = user["id"]
        flash("تم تسجيل الدخول بنجاح.", "success")

        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)

        return redirect(url_for("researcher_dashboard"))

    # ================== طلب GET ==================
    return render_template("researcher_login.html")

@app.route("/researcher/logout")
def researcher_logout():
    session.pop("user_id", None)
    flash("تم تسجيل الخروج.", "success")
    return redirect(url_for("researcher_login"))


# (اختياري) تفعيل حساب أول مرة / تغيير كلمة مرور، تقدرِين تضيفين route لاحقاً


# ===================== بروفايل الباحث =====================

@app.route("/researcher/profile", methods=["GET", "POST"])
@login_required
def researcher_profile():
    db = get_db()
    user = get_current_user()

    if request.method == "POST":
        name_ar = request.form.get("name_ar", "").strip()
        name_en = request.form.get("name_en", "").strip()
        email = request.form.get("email", "").strip()
        national_id = request.form.get("national_id", "").strip()
        sector = request.form.get("sector", "").strip()
        org_unit = request.form.get("org_unit", "").strip()
        rank_title = request.form.get("rank_title", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        if not name_ar or not email:
            flash("الاسم والبريد مطلوبان.", "error")
            return redirect(request.url)

        password_hash = user["password_hash"]
        if password:
            password_hash = generate_password_hash(password)

        avatar_storage = request.files.get("avatar")
        avatar_file = user["avatar_file"]

        new_avatar = save_uploaded_file(
            avatar_storage,
            UPLOAD_AVATARS,
            ALLOWED_IMG_EXT
        )
        if new_avatar:
            avatar_file = new_avatar

        db.execute(
            """
            UPDATE users
            SET name_ar = ?, name_en = ?, email = ?, national_id = ?,
                sector = ?, org_unit = ?, rank_title = ?, phone = ?,
                password_hash = ?, avatar_file = ?
            WHERE id = ?
            """,
            (
                name_ar, name_en, email, national_id,
                sector, org_unit, rank_title, phone,
                password_hash, avatar_file,
                user["id"],
            ),
        )
        db.commit()


        updated_user = db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user["id"],)
        ).fetchone()

    
        session["user_id"] = updated_user["id"]

        flash("تم تحديث ملفك الشخصي بنجاح.", "success")
        return redirect(url_for("researcher_profile"))

    user = get_current_user()
    return render_template("researcher_profile.html", user=user)


# ===================== لوحة تحكم الباحث =====================

@app.route("/researcher")
def researcher_index():
    # إعادة توجيه للوحة التحكم
    return redirect(url_for("researcher_dashboard"))


@app.route("/researcher/dashboard")
@login_required
def researcher_dashboard():
    db = get_db()
    user = get_current_user()

    # جلب كل الأبحاث المرتبطة بالمستخدم (باحث رئيس أو مشارك)
    cur = db.execute(
        """
        SELECT DISTINCT r.*
        FROM research_items r
        JOIN authors a ON a.research_id = r.id
        WHERE a.user_id = ?
           OR (a.email IS NOT NULL AND a.email != '' AND a.email = ?)
        ORDER BY r.created_at DESC
        """,
        (user["id"], user["email"]),
    )
    rows = cur.fetchall()

    # تقسيم حسب النوع
    researches = [r for r in rows if r["kind"] == "Research"]
    projects = [r for r in rows if r["kind"] != "Research"]

    stats = {
        "total_researches": len(researches),
        "total_projects": len(projects),
        "pending_items": 0,  # لو أضفتِ حالة status في الجدول، حدثي هذا
    }

    return render_template(
        "researcher_dashboard.html",
        current_user=user,
        researches=researches,
        projects=projects,
        stats=stats,
    )


# ===================== إضافة بحث جديد =====================

@app.route("/researcher/new", methods=["GET", "POST"])
@login_required
def researcher_new():
    db = get_db()
    current_user = get_current_user()

    if request.method == "POST":
        # ===== 1) معلومات البحث / المشروع =====
        title = request.form.get("title", "").strip()
        short = request.form.get("short_desc", "").strip()
        abstract = request.form.get("abstract", "").strip()
        kind = request.form.get("kind", "Research")
        year = request.form.get("year") or None
        field = request.form.get("field", "").strip()
        sector = request.form.get("sector", "").strip()
        confidentiality = request.form.get("conf", "public")
        publisher = request.form.get("publisher", "").strip()
        link_url = request.form.get("link", "").strip()

        if not title:
            flash("الرجاء إدخال عنوان البحث/المشروع.", "error")
            return redirect(request.url)

        # ملف البحث (اختياري)
        file_storage = request.files.get("file_upload")
        file_name = save_uploaded_file(file_storage, UPLOAD_RESEARCH, ALLOWED_DOC_EXT)

        cur = db.execute(
            """
            INSERT INTO research_items
              (title, short, abstract, kind, year, field, sector,
               confidentiality, publisher, link_url, file_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                short,
                abstract,
                kind,
                year,
                field,
                sector,
                confidentiality,
                publisher,
                link_url,
                file_name,
            ),
        )
        research_id = cur.lastrowid

        # ===== 2) الباحث الرئيسي =====
        main_name_ar = request.form.get("author_name_ar", "").strip()
        main_name_en = request.form.get("author_name_en", "").strip()
        main_rank = request.form.get("author_rank", "").strip()
        main_sector = request.form.get("author_sector", "").strip()
        main_dept = request.form.get("author_dept", "").strip()
        main_email = request.form.get("author_email", "").strip()
        main_phone = request.form.get("author_phone", "").strip()
        main_gender = request.form.get("author_gender", "male")

        main_avatar_storage = request.files.get("author_photo")
        main_avatar_file = save_uploaded_file(main_avatar_storage, UPLOAD_AVATARS, ALLOWED_IMG_EXT)

        # نحاول ربط الباحث الرئيسي بحسابه في users
        main_user_id = current_user["id"]
        if main_email and main_email != current_user["email"]:
            # لو كتب إيميل مختلف نحاول نبحث عنه
            cur = db.execute("SELECT id FROM users WHERE email = ?", (main_email,))
            row = cur.fetchone()
            if row:
                main_user_id = row["id"]

        if main_name_ar:
            db.execute(
                """
                INSERT INTO authors
                  (research_id, user_id, name_ar, name_en, rank_title,
                   sector, org_unit, email, phone, gender,
                   avatar_file, is_main)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    research_id,
                    main_user_id,
                    main_name_ar,
                    main_name_en,
                    main_rank,
                    main_sector,
                    main_dept,
                    main_email or current_user["email"],
                    main_phone,
                    main_gender,
                    main_avatar_file,
                ),
            )

        # ===== 3) الباحثون المشاركون (من الحقول الديناميكية) =====
        coauthors = defaultdict(dict)

        # نجمع حقول الفورم بشكل coauthors[index][field]
        for key, value in request.form.items():
            m = re.match(r"coauthors\[(\d+)\]\[(\w+)\]", key)
            if not m:
                continue
            idx, field_name = m.groups()
            coauthors[idx][field_name] = value.strip()

        # نجمع ملفات الصور لنفس الباحثين
        coauthor_photos = {}
        for key, fs in request.files.items():
            m = re.match(r"coauthors\[(\d+)\]\[photo\]", key)
            if not m:
                continue
            idx = m.group(1)
            coauthor_photos[idx] = fs

        for idx, data in coauthors.items():
            name_ar = data.get("name_ar", "").strip()
            if not name_ar:
                continue  # نتجاهل أي صف فاضي

            name_en = data.get("name_en", "").strip()
            rank = data.get("rank", "").strip()
            c_sector = data.get("sector", "").strip()
            dept = data.get("dept", "").strip()
            email = data.get("email", "").strip()
            phone = data.get("phone", "").strip()
            gender = data.get("gender", "male")

            avatar_file = None
            fs = coauthor_photos.get(idx)
            if fs:
                avatar_file = save_uploaded_file(fs, UPLOAD_AVATARS, ALLOWED_IMG_EXT)

            # نحاول نربطه بحساب مستخدم في users عن طريق البريد
            user_id = None
            if email:
                cur = db.execute("SELECT id FROM users WHERE email = ?", (email,))
                row = cur.fetchone()
                if row:
                    user_id = row["id"]

            db.execute(
                """
                INSERT INTO authors
                  (research_id, user_id, name_ar, name_en, rank_title,
                   sector, org_unit, email, phone, gender,
                   avatar_file, is_main)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    research_id,
                    user_id,
                    name_ar,
                    name_en,
                    rank,
                    c_sector,
                    dept,
                    email,
                    phone,
                    gender,
                    avatar_file,
                ),
            )

        db.commit()
        flash("تم حفظ البحث وبيانات الباحثين بنجاح.", "success")
        return redirect(url_for("researcher_dashboard"))

    # GET
    return render_template("researcher_form.html", mode="new", item=None, main_author=None, coauthors=[])


# ===================== تعديل بحث =====================

@app.route("/researcher/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def researcher_edit(item_id):
    db = get_db()
    current_user = get_current_user()

    # ===== جلب بيانات البحث =====
    cur = db.execute("SELECT * FROM research_items WHERE id = ?", (item_id,))
    item = cur.fetchone()
    if not item:
        flash("العنصر غير موجود.", "error")
        return redirect(url_for("researcher_dashboard"))

    # الباحث الرئيسي
    cur = db.execute(
        "SELECT * FROM authors WHERE research_id = ? AND is_main = 1 LIMIT 1",
        (item_id,),
    )
    main_author = cur.fetchone()

    # الباحثون المشاركون
    cur = db.execute(
        "SELECT * FROM authors WHERE research_id = ? AND is_main = 0",
        (item_id,),
    )
    coauthors = cur.fetchall()

    if request.method == "POST":
        # ===== 1) تحديث معلومات البحث / المشروع =====
        title = request.form.get("title", "").strip()
        short = request.form.get("short_desc", "").strip()
        abstract = request.form.get("abstract", "").strip()
        kind = request.form.get("kind", "Research")
        year = request.form.get("year") or None
        field = request.form.get("field", "").strip()
        sector = request.form.get("sector", "").strip()
        confidentiality = request.form.get("conf", "public")
        publisher = request.form.get("publisher", "").strip()
        link_url = request.form.get("link", "").strip()

        if not title:
            flash("الرجاء إدخال عنوان البحث/المشروع.", "error")
            return redirect(request.url)

        # ملف جديد (اختياري)
        file_storage = request.files.get("file_upload")
        file_name = item["file_name"]
        new_file_name = save_uploaded_file(file_storage, UPLOAD_RESEARCH, ALLOWED_DOC_EXT)
        if new_file_name:
            file_name = new_file_name

        db.execute(
            """
            UPDATE research_items
            SET title = ?, short = ?, abstract = ?, kind = ?, year = ?,
                field = ?, sector = ?, confidentiality = ?, publisher = ?,
                link_url = ?, file_name = ?
            WHERE id = ?
            """,
            (
                title,
                short,
                abstract,
                kind,
                year,
                field,
                sector,
                confidentiality,
                publisher,
                link_url,
                file_name,
                item_id,
            ),
        )

        # ===== 2) تحديث / إنشاء الباحث الرئيسي =====
        main_name_ar = request.form.get("author_name_ar", "").strip()
        main_name_en = request.form.get("author_name_en", "").strip()
        main_rank = request.form.get("author_rank", "").strip()
        main_sector = request.form.get("author_sector", "").strip()
        main_dept = request.form.get("author_dept", "").strip()
        main_email = request.form.get("author_email", "").strip()
        main_phone = request.form.get("author_phone", "").strip()
        main_gender = request.form.get("author_gender", "male")

        avatar_storage = request.files.get("author_photo")
        avatar_file = main_author["avatar_file"] if main_author else None
        new_avatar = save_uploaded_file(avatar_storage, UPLOAD_AVATARS, ALLOWED_IMG_EXT)
        if new_avatar:
            avatar_file = new_avatar

        # ربطه بحساب مستخدم
        main_user_id = current_user["id"]
        if main_email and main_email != current_user["email"]:
            cur = db.execute("SELECT id FROM users WHERE email = ?", (main_email,))
            row = cur.fetchone()
            if row:
                main_user_id = row["id"]

        if main_author:
            if main_name_ar:
                db.execute(
                    """
                    UPDATE authors
                    SET user_id = ?, name_ar = ?, name_en = ?, rank_title = ?,
                        sector = ?, org_unit = ?, email = ?, phone = ?,
                        gender = ?, avatar_file = ?, is_main = 1
                    WHERE id = ?
                    """,
                    (
                        main_user_id,
                        main_name_ar,
                        main_name_en,
                        main_rank,
                        main_sector,
                        main_dept,
                        main_email,
                        main_phone,
                        main_gender,
                        avatar_file,
                        main_author["id"],
                    ),
                )
            else:
                db.execute("DELETE FROM authors WHERE id = ?", (main_author["id"],))
        else:
            if main_name_ar:
                db.execute(
                    """
                    INSERT INTO authors
                      (research_id, user_id, name_ar, name_en, rank_title,
                       sector, org_unit, email, phone, gender,
                       avatar_file, is_main)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        item_id,
                        main_user_id,
                        main_name_ar,
                        main_name_en,
                        main_rank,
                        main_sector,
                        main_dept,
                        main_email,
                        main_phone,
                        main_gender,
                        avatar_file,
                    ),
                )

        # ===== 3) إعادة بناء الباحثين المشاركين =====
        db.execute(
            "DELETE FROM authors WHERE research_id = ? AND is_main = 0",
            (item_id,),
        )

        coauthors_data = defaultdict(dict)

        for key, value in request.form.items():
            m = re.match(r"coauthors\[(\d+)\]\[(\w+)\]", key)
            if not m:
                continue
            idx, field_name = m.groups()
            coauthors_data[idx][field_name] = value.strip()

        coauthor_photos = {}
        for key, fs in request.files.items():
            m = re.match(r"coauthors\[(\d+)\]\[photo\]", key)
            if not m:
                continue
            idx = m.group(1)
            coauthor_photos[idx] = fs

        for idx, data in coauthors_data.items():
            name_ar = data.get("name_ar", "").strip()
            if not name_ar:
                continue

            name_en = data.get("name_en", "").strip()
            rank = data.get("rank", "").strip()
            c_sector = data.get("sector", "").strip()
            dept = data.get("dept", "").strip()
            email = data.get("email", "").strip()
            phone = data.get("phone", "").strip()
            gender = data.get("gender", "male")

            avatar_file = None
            fs = coauthor_photos.get(idx)
            if fs:
                avatar_file = save_uploaded_file(fs, UPLOAD_AVATARS, ALLOWED_IMG_EXT)

            user_id = None
            if email:
                cur = db.execute("SELECT id FROM users WHERE email = ?", (email,))
                row = cur.fetchone()
                if row:
                    user_id = row["id"]

            db.execute(
                """
                INSERT INTO authors
                  (research_id, user_id, name_ar, name_en, rank_title,
                   sector, org_unit, email, phone, gender,
                   avatar_file, is_main)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    item_id,
                    user_id,
                    name_ar,
                    name_en,
                    rank,
                    c_sector,
                    dept,
                    email,
                    phone,
                    gender,
                    avatar_file,
                ),
            )

        db.commit()
        flash("تم تحديث بيانات البحث والباحثين بنجاح.", "success")
        return redirect(url_for("researcher_dashboard"))

    # GET: عرض النموذج مع البيانات الحالية
    return render_template(
        "researcher_form.html",
        mode="edit",
        item=item,
        main_author=main_author,
        coauthors=coauthors,
    )


# ===================== عرض تفاصيل بحث من بوابة الباحثين =====================

@app.route("/researcher/<int:item_id>/view")
@login_required
def researcher_view(item_id):
    db = get_db()

    cur = db.execute("SELECT * FROM research_items WHERE id = ?", (item_id,))
    item = cur.fetchone()
    if not item:
        flash("العنصر غير موجود.", "error")
        return redirect(url_for("researcher_dashboard"))

    cur = db.execute(
        """
        SELECT *
        FROM authors
        WHERE research_id = ?
        ORDER BY is_main DESC, id ASC
        """,
        (item_id,),
    )
    authors = cur.fetchall()

    return render_template(
        "researcher_detail.html",
        item=item,
        authors=authors,
    )


# ===================== الملفات المرفوعة =====================

@app.route("/uploads/research/<path:filename>")
def uploaded_research(filename):
    return send_from_directory(UPLOAD_RESEARCH, filename, as_attachment=False)


@app.route("/uploads/avatars/<path:filename>")
def uploaded_avatar(filename):
    return send_from_directory(UPLOAD_AVATARS, filename, as_attachment=False)


@app.route("/uploads/avatars/<path:filename>")
def avatar_file(filename):
    return send_from_directory(UPLOAD_AVATARS, filename)

# ===================== تشغيل التطبيق =====================

def bootstrap():
    with app.app_context():
        # لو عندك إنشاء جداول الأدمن
        # ensure_admin_schema()

        migrate_innovations()



# ===================== تشغيل التطبيق =====================
if __name__ == "__main__":
    bootstrap()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
