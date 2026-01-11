(function () {
  const cfg = window.PAGE || {};
  const id = cfg.id;
  if (!id) return;

  const fromDb = cfg.source === "db" && cfg.dbItem;

  // بيانات الموك من base.html (لما نكون في وضع العرض التجريبي / القطاع)
  const mock = window.MOCK || {};
  const sectors = mock.sectors || [];
  const mockItems = mock.items || [];
  const mockAuthors = mock.authors || {};
  const mockAtts = mock.attachments || {};

  let item;
  let authors = [];
  let attList = [];

  // ===============================
  // 1) نحدد مصدر البيانات: DB أو MOCK
  // ===============================
  if (fromDb) {
    // 🔹 جاي من قاعدة البيانات
    item = cfg.dbItem;
    authors = cfg.dbAuthors || [];

    // المرفقات من حقول الداتابيس
    if (item.file_name) {
      attList.push({
        kind: "PDF",
        label: "الملف البحثي (من قاعدة البيانات)",
        url: "/uploads/research/" + item.file_name
      });
    }

    if (item.link_url) {
      attList.push({
        kind: "Link",
        label: "رابط جهة النشر / المستودع",
        url: item.link_url
      });
    }

  } else {
    // 🔹 جاي من بيانات MOCK
    item = mockItems.find(i => i.id === id);
    authors = mockAuthors[id] || [];
    attList = mockAtts[id] || [];
  }

  if (!item) {
    const container = document.querySelector(".detail-wrapper") || document.querySelector(".detail");
    if (container) {
      container.innerHTML = "<p>لم يتم العثور على العنصر.</p>";
    }
    return;
  }

  // ===============================
  // 2) القطاع
  // ===============================
  const sectorObj = sectors.find(s => s.slug === item.sector);
  const sectorName = sectorObj ? sectorObj.name : "قطاع وزارة الداخلية";

  // ===============================
  // 3) عناصر DOM
  // ===============================
  const titleEl = document.getElementById("detailTitle");
  const shortEl = document.getElementById("detailShort");
  const sectorEl = document.getElementById("detailSector");
  const yearEl = document.getElementById("detailYear");
  const fieldEl = document.getElementById("detailField");
  const publisherEl = document.getElementById("detailPublisher");
  const typeTagEl = document.getElementById("detailTypeTag");
  const confTagEl = document.getElementById("detailConfTag");
  const summaryEl = document.getElementById("detailSummary");
  const authorsEl = document.getElementById("detailAuthors");
  const linksEl = document.getElementById("detailLinks");

  // ===============================
  // 4) تجهيز نوع العنصر + السرية
  // ===============================
  const rawType = fromDb
    ? (item.kind || "Research")
    : (item.type || "Research");

  let typeLabel = "بحث";
  if (rawType === "Project") typeLabel = "مشروع";
  else if (rawType === "Innovation") typeLabel = "ابتكار";

  const isConf = fromDb
    ? (item.confidentiality && item.confidentiality !== "public")
    : !!item.conf;

  // ===============================
  // 5) تعبئة العنوان / الوصف / الميتا
  // ===============================
  if (titleEl) titleEl.textContent = item.title || "—";

  const shortText = fromDb
    ? (item.short || "")
    : (item.short || item.brief || "");

  if (shortEl) shortEl.textContent = shortText;

  if (sectorEl) sectorEl.textContent = sectorName;
  if (yearEl) yearEl.textContent = item.year || "-";
  if (fieldEl) fieldEl.textContent = item.field || "غير مصنف";
  if (publisherEl) publisherEl.textContent = item.publisher || "غير محددة";

  if (typeTagEl) {
    typeTagEl.textContent = typeLabel;
    typeTagEl.classList.add("badge-type-" + rawType.toLowerCase());
  }

  if (confTagEl) {
    confTagEl.textContent = isConf ? "سري" : "عام";
    confTagEl.classList.toggle("badge-confidential", isConf);
    confTagEl.classList.toggle("badge-public", !isConf);
  }

  const summaryText = fromDb
    ? (item.abstract || item.short || "")
    : (item.summary || item.brief || item.short || "");

  if (summaryEl) {
    summaryEl.textContent = summaryText;
  }

  // ===============================
  // 6) دالة رسم الباحثين (تستخدم DB أو MOCK)
  // ===============================
function renderAuthors(list) {
  if (!authorsEl) return;

  if (!list || !list.length) {
    authorsEl.innerHTML = `
      <p class="muted">لا توجد بيانات باحثين مسجلة لهذا العمل حتى الآن.</p>
    `;
    return;
  }

  authorsEl.innerHTML = list.map(a => {
    const name = a.name || a.name_ar || "";
    const rank = a.rank || a.rank_title || "";

    // اسم القطاع العربي
    let sectorLabel = a.sector || "";
    if (sectors && Array.isArray(sectors)) {
      const sec = sectors.find(s => s.slug === a.sector);
      if (sec) sectorLabel = sec.name;
    }

    const unit = a.unit || a.org_unit || a.org || "";
    const email = a.email || "";
    const phone = a.phone || "";
    const gender = (a.gender || "").toLowerCase();

    // ===========================
    // اختيار الصورة الافتراضية (أيقونة)
    // ===========================
    let photo = "";

    if (a.avatar_file) {
      // صور مرفوعة
      photo = "/uploads/avatars/" + a.avatar_file;
    } else if (a.photo) {
      // صور من MOCK
      photo = a.photo;
    } else {
      // أيقونات افتراضية حسب الجنس
      if (gender === "f" || gender === "female" || gender === "أنثى" || gender === "انثى") {
        photo = null; // نستخدم أيقونة امرأة
      } else {
        photo = null; // نستخدم أيقونة رجل
      }
    }

    // ===========================
    // بناء HTML حسب وجود صورة أو أيقونة
    // ===========================
    let avatarHTML = "";

    if (photo) {
      avatarHTML = `
        <div class="author-avatar">
          <img src="${photo}" alt="${name}">
        </div>
      `;
    } else {
      // أيقونة بدايل
      const icon = (gender === "f" || gender === "female" || gender === "أنثى")
        ? "bi-person-fill"
        : "bi-person";

      avatarHTML = `
        <div class="author-avatar icon-avatar female">
          <i class="bi ${icon}"></i>
        </div>
      `;

    }

    return `
      <article class="author-card">
        ${avatarHTML}
        <div class="author-body">
          <h3 class="author-name">${name}</h3>
          <p class="author-rank">${rank}</p>
          <p class="author-unit">
            ${unit ? unit + " – " : ""}${sectorLabel}
          </p>

          <div class="author-meta">
            ${email ? `
              <div>
                <i class="bi bi-envelope"></i>
                <span>${email}</span>
              </div>` : ""}
            ${phone ? `
              <div>
                <i class="bi bi-telephone"></i>
                <span>${phone}</span>
              </div>` : ""}
          </div>
        </div>
      </article>
    `;
  }).join("");
}

  renderAuthors(authors);

  // ===============================
  // 7) المرفقات / الروابط + زر التمويل
  // ===============================
  if (linksEl) {
    let html = "";

    if (attList && attList.length) {
      html += attList.map(a => {
        let icon = "bi-file-earmark-text";
        let title = a.label || "ملف مرفق";
        let meta = "الاطلاع على الملف أو الرابط المرتبط بالبحث.";

        if (a.kind === "PDF") {
          icon = "bi-file-earmark-pdf";
          meta = "عرض نسخة كاملة من البحث أو العرض التقديمي.";
        } else if (a.kind === "Link") {
          icon = "bi-box-arrow-up-right";
          meta = "الانتقال إلى صفحة البحث أو النظام على الجهة الناشرة.";
        }

        return `
          <a href="${a.url || '#'}" target="_blank" rel="noopener" class="detail-link-row">
            <span class="detail-link-icon">
              <i class="bi ${icon}"></i>
            </span>
            <span class="detail-link-body">
              <span class="detail-link-title">${title}</span>
              <span class="detail-link-meta">${meta}</span>
            </span>
          </a>
        `;
      }).join("");
    } else {
      html += `
        <p class="muted">لا توجد ملفات أو روابط مرفقة حاليًا.</p>
      `;
    }

    // زر ثابت لطلب تبنّي أو تمويل هذا البحث
    html += `
      <a href="#" class="detail-link-row">
        <span class="detail-link-icon">
          <i class="bi bi-hand-index-thumb"></i>
        </span>
        <span class="detail-link-body">
          <span class="detail-link-title">طلب تبنّي أو تمويل هذا البحث</span>
          <span class="detail-link-meta">
            في حال رغبتكم بتبنّي الفكرة أو تمويل تطويرها إلى مشروع أو تطبيق داخل الجهة.
          </span>
        </span>
      </a>
    `;

    linksEl.innerHTML = html;

    if (isConf) {
      linksEl.insertAdjacentHTML(
        "beforeend",
        `
        <p class="detail-note-conf">
          هذا البحث مصنّف كـ <strong>سري</strong>، ويمكن للجهات المختصة طلب الوصول التفصيلي عبر القنوات الرسمية.
        </p>
        `
      );
    }
  }

  // ===============================
  // 8) QR Code
  // ===============================
  const qrEl = document.getElementById("qrcode");
  if (qrEl && window.QRCode) {
    qrEl.innerHTML = "";
    new QRCode(qrEl, {
      text: window.location.href,
      width: 140,
      height: 140,
    });
  }
})();
