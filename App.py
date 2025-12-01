import os
import sqlite3
import re
from collections import defaultdict
from functools import wraps

from flask import (
    Flask, g, render_template, request,
    redirect, url_for, flash, send_from_directory,
    session
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-me"   # غيّريها لشيء آمن

# إعداد مجلدات الرفع
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
UPLOAD_RESEARCH = os.path.join(UPLOAD_ROOT, "research")
UPLOAD_AVATARS = os.path.join(UPLOAD_ROOT, "avatars")

os.makedirs(UPLOAD_RESEARCH, exist_ok=True)
os.makedirs(UPLOAD_AVATARS, exist_ok=True)

ALLOWED_DOC_EXT = {"pdf", "doc", "docx", "ppt", "pptx"}
ALLOWED_IMG_EXT = {"png", "jpg", "jpeg", "gif"}

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
    يرجّع اسم الملف المحفوظ أو None لو ما فيه رفع / امتداد غير مسموح.
    """
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename, allowed_ext):
        return None

    filename = secure_filename(file_storage.filename)
    base, ext = os.path.splitext(filename)
    # رقم بسيط لتمييز الاسم
    final_name = f"{base}_{int(os.path.getmtime(__file__))}{ext}"
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
            flash("يجب تسجيل الدخول للوصول إلى بوابة الباحثين.", "error")
            return redirect(url_for("researcher_login"))
        return view_func(*args, **kwargs)
    return wrapped


# ===================== صفحات عامة =====================

# صفحة الهبوط الرئيسية /
@app.route("/")
def landing():
    start_clicks = get_metric("about_start_clicks", 0)
    return render_template("landing.html", start_clicks=start_clicks)


# صفحة بوابة المنصة /portal
@app.route("/portal")
def index():
    return render_template("index.html")


# زر "ابدأ" في صفحة الهبوط
@app.route("/start")
def start():
    increment_metric("about_start_clicks", 1)
    return redirect(url_for("index"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/sector/<slug>")
def sector(slug):
    return render_template("sector.html", slug=slug)


@app.route("/detail/<int:item_id>")
def detail(item_id):
    return render_template("detail.html", item_id=item_id)


@app.route("/dashboard")
def dashboard():
    start_clicks = get_metric("about_start_clicks", 0)
    return render_template("dashboard.html", start_clicks=start_clicks)

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

from flask import session, flash, redirect, url_for, render_template, request
# تأكدي إن عندك import لـ session فوق

@app.route("/researcher/login", methods=["GET", "POST"])
def researcher_login():
    db = get_db()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("الرجاء إدخال بيانات الدخول.", "error")
            return redirect(request.url)

        cur = db.execute(
            """
            SELECT * FROM users
            WHERE email = ? OR national_id = ?
            LIMIT 1
            """,
            (username, username),
        )
        user = cur.fetchone()

        # 🔹 مقارنة عادية بدون هاش (فقط لغرض الاختبار)
        if not user or user["password_hash"] != password:
            flash("بيانات الدخول غير صحيحة.", "error")
            return redirect(request.url)

        session["user_id"] = user["id"]
        flash("تم تسجيل الدخول بنجاح.", "success")
        return redirect(url_for("researcher_dashboard"))

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
        new_avatar = save_uploaded_file(avatar_storage, UPLOAD_AVATARS, ALLOWED_IMG_EXT)
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


# ===================== تشغيل التطبيق =====================

if __name__ == "__main__":
    app.run(debug=True)
