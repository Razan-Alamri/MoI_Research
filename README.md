research360/
├─ app.py                      # نقطة تشغيل Flask
├─ config.py                   # الإعدادات (ENV, DB URI, SECRET)
├─ requirements.txt            # الحزم
├─ instance/
│  └─ research360.sqlite       # قاعدة البيانات (وقت المعرض)
├─ research360/
│  ├─ __init__.py
│  ├─ extensions.py            # تهيئة SQLAlchemy, Marshmallow, CORS
│  ├─ models.py                # Sector, Research, Author, Attachment, Many-to-Many
│  ├─ schemas.py               # مخططات إخراج JSON (Marshmallow)
│  ├─ seeds.py                 # سكربت تعبئة بيانات تجريبية للمعرض
│  ├─ api/
│  │  ├─ __init__.py
│  │  ├─ sectors.py            # /api/sectors, /api/sectors/<id or slug>
│  │  ├─ research.py           # /api/research/<id>, /api/search
│  │  └─ stats.py              # /api/stats/summary, /api/stats/by_sector, /by_year, /by_field
│  ├─ services/
│  │  ├─ qr_service.py         # توليد QR (Pillow/qrcode) أو إرجاع PNG
│  │  └─ files_service.py      # صلاحيات/وصول المرفقات (سري/غير سري)
│  ├─ security/
│  │  └─ access_policies.py    # سياسات إظهار/إخفاء وروابط الطلب
│  ├─ utils/
│  │  └─ helpers.py            # أدوات عامة (pagination, slugify...)
│  ├─ blueprints.py            # تسجيل الـ Blueprints
│  └─ web/
│     ├─ templates/
│     │  ├─ base.html          # إطار عام (head, scripts, styles)
│     │  ├─ index.html         # الصفحة الرئيسية (الدوائر 3D + الشريط)
│     │  ├─ sector.html        # صفحة القطاع
│     │  ├─ detail.html        # صفحة التفاصيل (QR/تحميل/طلب وصول)
│     │  └─ dashboard.html     # لوحة الإحصاءات
│     └─ static/
│        ├─ css/
│        │  ├─ main.css        # أنماط عامة
│        │  └─ theme.css       # ألوان/Glow/Night mode
│        ├─ js/
│        │  ├─ main.js         # تهيئة عامة + ربط API
│        │  ├─ index.js        # منطق الصفحة الرئيسية (Three.js Orbital)
│        │  ├─ sector.js       # جلب المشاريع + الفلاتر + بطاقات
│        │  ├─ detail.js       # عرض البحث + QR
│        │  └─ dashboard.js    # الرسوم البيانية (Chart.js / ECharts)
│        ├─ js/lib/
│        │  ├─ three.min.js
│        │  ├─ chart.umd.js
│        │  └─ qrcode.min.js   # بديل توليد QR على المتصفح عند الحاجة
│        ├─ img/
│        │  ├─ logo_moi.svg
│        │  ├─ sectors/        # شعارات القطاعات (svg/png)
│        │  └─ avatars/        # صور الباحثين إن وجدت
│        └─ downloads/
│           └─ samples/        # ملفات PDF/IEEE العامة (غير سرية)
└─ README.md                   # تعليمات التشغيل السريع
