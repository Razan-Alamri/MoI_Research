import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

DB_PATH = "data.db"

def seed():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    # --- taxonomy sectors ---
    sectors = [
        ("prisons", "المديرية العامة للسجون"),
        ("traffic", "الإدارة العامة للمرور"),
        ("civil_defense", "الدفاع المدني"),
        ("passports", "الجوازات"),
    ]
    for key, ar in sectors:
        db.execute("""
          INSERT OR IGNORE INTO taxonomy (type, key, label_ar, label_en, is_active, sort_order)
          VALUES ('sector', ?, ?, NULL, 1, 0)
        """, (key, ar))

    # --- admin user ---
    db.execute("""
      INSERT OR IGNORE INTO admin_users (id, username, name_ar, email, password_hash, role, is_active)
      VALUES (1, 'admin', 'مشرف النظام', 'admin@example.com', 'DEMO_HASH', 'admin', 1)
    """)

    # --- researchers/users ---
    db.execute("""
      INSERT OR IGNORE INTO users (id, name_ar, name_en, email, national_id, sector, org_unit, rank_title, phone, password_hash, role)
      VALUES
      (1,'أحمد العتيبي','Ahmed Alotaibi','ahmed@example.com','1','prisons','وحدة الابتكار','باحث','0500000001','DEMO_HASH','researcher'),
      (2,'نورة الشهري','Noura Alshahri','noura@example.com','2','traffic','مركز البيانات','باحث','0500000002','DEMO_HASH','researcher')
    """)

    # --- innovations ---
    db.execute("""
      INSERT OR IGNORE INTO innovations
      (id, name, email, phone_display, category, idea, status, source, priority, assigned_to, review_notes)
      VALUES
      (1,'سارة','sara@mail.com','0501234567','خدمات','فكرة منصة لتسريع تبنّي الابتكارات','new','visitor','normal',NULL,NULL),
      (2,'مها','maha@mail.com','0507654321','تحليلات','لوحة مؤشرات للابتكار حسب القطاع','in_review','researcher','high',1,'جارٍ المراجعة'),
      (3,'خالد','khaled@mail.com',NULL,'أتمتة','أتمتة مسار تقييم الأفكار','done','admin','normal',1,'تم الاعتماد')
    """)

    # --- partner requests ---
    db.execute("""
      INSERT OR IGNORE INTO partner_requests
      (id, org_name, contact_name, email, request_type, details, status, assigned_to)
      VALUES
      (1,'شركة تقنية','محمد','corp@example.com','شراكة تطوير','طلب شراكة لتطوير نموذج ذكاء','new',1),
      (2,'جامعة','د.سلمان','uni@example.com','بحث مشترك','تعاون بحثي في الابتكار','in_review',1),
      (3,'جهة حكومية','أ.ريم','gov@example.com','تكامل','تكامل بيانات لرفع جودة المؤشرات','done',1)
    """)

    # --- research items (content workflow) ---
    db.execute("""
      INSERT OR IGNORE INTO research_items
      (id, title, kind, field, year, sector, workflow_status, reviewed_by, reviewed_at)
      VALUES
      (1,'دراسة عن تبنّي الابتكار في القطاعات','بحث','ابتكار',2025,'prisons','pending',NULL,NULL),
      (2,'تحليل مؤشرات الأداء للابتكار','تقرير','تحليلات',2024,'traffic','needs_changes',1,datetime('now')),
      (3,'دليل حوكمة المحتوى','دليل','حوكمة',2025,'prisons','published',1,datetime('now')),
      (4,'تقرير شراكات الابتكار','تقرير','شراكات',2023,'civil_defense','rejected',1,datetime('now'))
    """)

    db.commit()


    db.commit()
    db.close()
    print("✅ Done.")

if __name__ == "__main__":
    seed()

# import sqlite3

# DB = "data.db"

# def main():
#     con = sqlite3.connect(DB)
#     con.row_factory = sqlite3.Row
#     cur = con.cursor()

#     tables = cur.execute("""
#         SELECT name FROM sqlite_master
#         WHERE type='table' AND name NOT LIKE 'sqlite_%'
#         ORDER BY name
#     """).fetchall()

#     print("=== TABLES ===")
#     for t in tables:
#         tn = t["name"]
#         print("\n#", tn)

#         cols = cur.execute(f"PRAGMA table_info({tn})").fetchall()
#         for c in cols:
#             print(f"  - {c['name']} | {c['type']} | notnull={c['notnull']} | pk={c['pk']} | default={c['dflt_value']}")

#         fks = cur.execute(f"PRAGMA foreign_key_list({tn})").fetchall()
#         if fks:
#             print("  Foreign Keys:")
#             for fk in fks:
#                 print(f"    - {fk['from']} -> {fk['table']}.{fk['to']} (on_update={fk['on_update']}, on_delete={fk['on_delete']})")

#     print("\n=== INTEGRITY CHECK ===")
#     print(cur.execute("PRAGMA integrity_check;").fetchone()[0])

#     con.close()

# if __name__ == "__main__":
#     main()
