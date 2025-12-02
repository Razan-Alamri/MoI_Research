(function () {
  // نتحقق من وجود الـ slug والـ MOCK
  const slug = window.PAGE && window.PAGE.slug;
  if (!slug || !window.MOCK) return;

  const sectors = window.MOCK.sectors || [];
  const allItems = window.MOCK.items || [];
  const authorsMap = window.MOCK.authors || {};

  // القطاع الحالي
  const sector = sectors.find(s => s.slug === slug);
  const items = allItems.filter(it => it.sector === slug);

  // عناصر الـ DOM
  const logoEl = document.getElementById("sectorLogo");
  const nameEl = document.getElementById("sectorName");
  const cardsWrap = document.getElementById("cardsWrap");

  // عناصر KPIs
  const kpiTotalEl = document.getElementById("kpiTotal");
  const kpiResearchEl = document.getElementById("kpiResearch");
  const kpiProjectEl = document.getElementById("kpiProject");
  const kpiInnovationEl = document.getElementById("kpiInnovation");
  const kpiAuthorsEl = document.getElementById("kpiAuthors");

  // الفلاتر
  const filterTypeEl = document.getElementById("filterType");
  const filterYearEl = document.getElementById("filterYear");
  const filterConfEl = document.getElementById("filterConf");
  const filterFieldEl = document.getElementById("filterField");

  // =========================
  // تعبئة الهيدر (الاسم + الشعار)
  // =========================
  if (sector && logoEl && nameEl) {
    nameEl.textContent = sector.name;
    logoEl.innerHTML = `
      <img src="${sector.logo || '/static/img/logo_moi.png'}"
           alt="${sector.name}">
    `;
  }

  // =========================
  //  أيقونة لكل مجال
  // =========================
  const fieldIconMap = {
    "ذكاء اصطناعي": "bi-cpu",
    "أمن سيبراني": "bi-shield-lock",
    "أنظمة معلومات": "bi-pc-display",
    "تحليلات تشغيلية": "bi-graph-up",
    "رؤية حاسوبية": "bi-eye",
    "روبوتات": "bi-robot",
    "درونز": "bi-airplane",
    "استشعار عن بعد": "bi-broadcast",
    "تجربة المستخدم": "bi-ui-checks-grid",
    "أنظمة معلومات صحية": "bi-hospital",
    "منصات بيانات": "bi-database",
    "تحول رقمي": "bi-arrows-repeat"
  };

  // =========================
  // KPI's (العناصر)
  // =========================
  const total = items.length;
  const totalResearch = items.filter(i => i.type === "Research").length;
  const totalProject = items.filter(i => i.type === "Project").length;
  const totalInnovation = items.filter(i => i.type === "Innovation").length;

  if (kpiTotalEl) kpiTotalEl.textContent = total;
  if (kpiResearchEl) kpiResearchEl.textContent = totalResearch;
  if (kpiProjectEl) kpiProjectEl.textContent = totalProject;
  if (kpiInnovationEl) kpiInnovationEl.textContent = totalInnovation;

  // ✅ KPI عدد الباحثين في هذا القطاع
  const authorSet = new Set();
  items.forEach(it => {
    const list = authorsMap[it.id] || [];
    list.forEach(a => {
      const key = a.email || a.name;
      if (key) authorSet.add(key);
    });
  });
  const authorsCount = authorSet.size;
  if (kpiAuthorsEl) kpiAuthorsEl.textContent = authorsCount;

  // =========================
  // تعبئة فلتر "المجال" ديناميكياً
  // =========================
  if (filterFieldEl) {
    const fields = [...new Set(items.map(i => i.field).filter(Boolean))];
    fields.forEach(f => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      filterFieldEl.appendChild(opt);
    });
  }

  // =========================
  // تحويل النوع إلى مسمى عربي
  // =========================
  function getTypeLabel(type) {
    if (type === "Project") return "مشروع";
    if (type === "Innovation") return "ابتكار";
    return "بحث";
  }

  // =========================
  // رسم البطاقات حسب الفلاتر
  // =========================
  function render() {
    if (!cardsWrap) return;

    const t = filterTypeEl ? filterTypeEl.value : "";
    const y = filterYearEl ? filterYearEl.value : "";
    const f = filterFieldEl ? filterFieldEl.value : "";
    const c = filterConfEl ? filterConfEl.value : "";

    const filtered = items.filter(i => {
      let ok = true;
      if (t && i.type !== t) ok = false;
      if (y && String(i.year) !== y) ok = false;
      if (f && i.field !== f) ok = false;
      if (c === "public" && i.conf) ok = false; // نعرض العام فقط
      if (c === "conf" && !i.conf) ok = false;  // نعرض السري فقط
      return ok;
    });

    if (!filtered.length) {
      cardsWrap.innerHTML = `
        <p style="text-align:center; color:var(--muted); margin-top:24px;">
          لا توجد عناصر مطابقة للفلاتر الحالية.
        </p>
      `;
      return;
    }

    cardsWrap.innerHTML = filtered.map(i => {
      const typeLabel = getTypeLabel(i.type);
      const statusLabel = i.conf ? "سري" : "عام";

      const shortTxt =
        i.short
          ? i.short
          : (i.brief ? i.brief.substring(0, 80) + "..." : "");

      const iconClass = fieldIconMap[i.field] || "bi-bookmark-star";

      return `
        <div class="card" onclick="location.href='/detail/${i.id}'">
          <div class="header">
            <div>
              <a class="title" href="/detail/${i.id}">
                ${i.title}
              </a>
              <p class="name">
                ${typeLabel} • ${i.field || "غير مصنف"} • ${i.year || "-"}
                
              </p>

              ${i.conf
          ? `<span class="tag-status tag-conf">${statusLabel}</span>`
          : `<span class="tag-status tag-public">${statusLabel}</span>`
        }
            </div>

            <span class="image">
              <i class="bi ${iconClass}"></i>
            </span>
          </div>

          <p class="description">
            ${shortTxt}
          </p>

   
        </div>
      `;
    }).join("");
  }

  // ربط الفلاتر بإعادة الرسم
  [filterTypeEl, filterYearEl, filterConfEl, filterFieldEl].forEach(el => {
    if (el) el.addEventListener("change", render);
  });

  // أول رسم عند فتح الصفحة
  render();
})();
