(function () {
  const id = window.PAGE?.id;
  if (!id || !window.MOCK) return;

  const items = window.MOCK.items || [];
  const authorsMap = window.MOCK.authors || {};
  const attsMap = window.MOCK.attachments || {};
  const sectors = window.MOCK.sectors || [];

  const item = items.find(i => i.id === id);
  if (!item) {
    const container = document.querySelector(".detail-wrapper") || document.querySelector(".detail");
    if (container) {
      container.innerHTML = "<p>لم يتم العثور على العنصر.</p>";
    }
    return;
  }

  // القطاع
  const sectorObj = sectors.find(s => s.slug === item.sector);
  const sectorName = sectorObj ? sectorObj.name : "قطاع وزارة الداخلية";

  // عناصر DOM
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

  // العنوان والوصف المختصر
  if (titleEl) titleEl.textContent = item.title || "—";
  if (shortEl) shortEl.textContent = item.short || item.brief || "";

  // ميتا
  if (sectorEl) sectorEl.textContent = sectorName;
  if (yearEl) yearEl.textContent = item.year || "-";
  if (fieldEl) fieldEl.textContent = item.field || "غير مصنف";
  if (publisherEl) publisherEl.textContent = item.publisher || "غير محددة";

  // نوع العنصر بالعربي
  let typeLabel = "بحث";
  if (item.type === "Project") typeLabel = "مشروع";
  if (item.type === "Innovation") typeLabel = "ابتكار";

  if (typeTagEl) {
    typeTagEl.textContent = typeLabel;
    typeTagEl.classList.add("badge-type-" + (item.type || "Research").toLowerCase());
  }

  // سري / عام
  const isConf = !!item.conf;
  if (confTagEl) {
    confTagEl.textContent = isConf ? "سري" : "عام";
    confTagEl.classList.toggle("badge-confidential", isConf);
    confTagEl.classList.toggle("badge-public", !isConf);
  }

  // الملخص (150–250 كلمة في الداتا)
  if (summaryEl) {
    summaryEl.textContent = item.summary || item.brief || "";
  }

  // الباحثون
  const authList = authorsMap[id] || [];
  if (authorsEl) {
    if (!authList.length) {
      authorsEl.innerHTML = `
        <p class="muted">لا توجد بيانات باحثين مسجلة لهذا العمل حتى الآن.</p>
      `;
    } else {
      authorsEl.innerHTML = authList.map(a => {
        const name = a.name || "";
        const rank = a.rank || "";
        const sector = a.sector || "";
        const unit = a.unit || a.org || "";
        const email = a.email || "";
        const phone = a.phone || "";
        const photo = a.photo || "/static/img/authors/placeholder.png";

        return `
          <article class="author-card">
            <div class="author-avatar">
              <img src="${photo}" alt="${name}">
            </div>
            <div class="author-body">
              <h3 class="author-name">${name}</h3>
              <p class="author-rank">${rank}</p>
              <p class="author-unit">
                ${unit ? unit + " – " : ""}${sector}
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
  }

  // المرفقات / الوصول
  const attList = attsMap[id] || [];
  if (linksEl) {
    if (isConf) {
      // سري: طلب وصول فقط
      linksEl.innerHTML = `
        <p class="muted">
          هذه المبادرة مصنّفة <strong>سري</strong>.
          يمكن طلب الوصول عبر الجهات الرسمية الناشرة للبحث.
        </p>
        <button class="btn-ghost" type="button">
          <i class="bi bi-shield-lock"></i>
          طلب وصول (نموذج تجريبي)
        </button>
      `;
    } else if (!attList.length) {
      linksEl.innerHTML = `
        <p class="muted">لا توجد ملفات أو روابط مرفقة حاليًا.</p>
      `;
    } else {
      linksEl.innerHTML = attList.map(a => {
        let icon = "bi-file-earmark-text";
        if (a.kind === "PDF") icon = "bi-file-earmark-pdf";
        if (a.kind === "Link") icon = "bi-link-45deg";

        return `
          <div class="detail-link-item">
            <span class="detail-link-icon">
              <i class="bi ${icon}"></i>
            </span>
            <a href="${a.url || '#'}" target="_blank" rel="noopener">
              ${a.label || 'ملف'}
            </a>
            <span class="detail-link-kind">${a.kind || ""}</span>
          </div>
        `;
      }).join("");
    }
  }

  // QR الكود
  const qrEl = document.getElementById("qrcode");
  if (qrEl && window.QRCode) {
    qrEl.innerHTML = "";
    new QRCode(qrEl, {
      text: window.location.href,
      width: 140,
      height: 140
    });
  }
})();
