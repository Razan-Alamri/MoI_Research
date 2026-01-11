(function () {
  const q = (window.SEARCH_QUERY || "").trim();
  const dbRows = window.SEARCH_DB_RESULTS || [];
  const mock = window.MOCK || {};
  const mockItems = mock.items || [];
  const authorsMap = mock.authors || {};
  const cardsWrap = document.getElementById("cardsWrap");

  if (!cardsWrap) return;

  // ========== 1) تجهيز نتائج قاعدة البيانات ==========
  const dbItems = dbRows.map(r => {
    // تحويل السرية لفلاغ مثل i.conf في sector.js
    const isConf =
      r.confidentiality === "conf" ||
      r.confidentiality === "سري" ||
      r.confidentiality === "confidential" ||
      r.confidentiality === 1;

    return {
      id: r.id,
      title: r.title,
      short: r.short || "",
      brief: r.abstract || "",
      type: r.type || "Research",
      year: r.year,
      field: r.field,
      sector: r.sector,
      conf: isConf
    };
  });

  // ========== 2) تجهيز نتائج MOCK (بحث نصي في الذاكرة) ==========
  function matchesQuery(item, q) {
    if (!q) return true;
    const text = [
      item.title || "",
      item.short || "",
      item.summary || "",
      item.field || "",
      item.sector || ""
    ].join(" ").toLowerCase();
    return text.includes(q.toLowerCase());
  }

  const mockMatches = q
    ? mockItems.filter(it => matchesQuery(it, q))
    : [];

  // ندمج الاثنين ونحذف أي تكرار بناءً على id
  const mergedMap = new Map();

  dbItems.forEach(it => {
    mergedMap.set(String(it.id), it);
  });

  mockMatches.forEach(it => {
    const key = String(it.id);
    if (!mergedMap.has(key)) {
      mergedMap.set(key, {
        id: it.id,
        title: it.title,
        short: it.short || "",
        brief: it.summary || "",
        type: it.type,
        year: it.year,
        field: it.field,
        sector: it.sector,
        conf: !!it.conf
      });
    }
  });

  const allResults = Array.from(mergedMap.values());

  // ========== 3) نفس خريطة الأيقونات من sector.js ==========
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
    "تحول رقمي": "bi-arrow-repeat"
  };

  function getTypeLabel(type) {
    if (type === "Project") return "مشروع";
    if (type === "Innovation") return "ابتكار";
    return "بحث";
  }

  const prefix = window.DETAIL_URL_PREFIX || "/detail/";

  // ========== 4) رسم البطاقات بنفس كود sector.js ==========
  function renderCards() {
    if (!allResults.length) {
      cardsWrap.innerHTML = `
        <p style="text-align:center; color:var(--muted); margin-top:24px;">
          لا توجد نتائج مطابقة لعبارة البحث الحالية.
        </p>
      `;
      return;
    }

    const html = allResults.map(i => {
      const typeLabel = getTypeLabel(i.type);
      const statusLabel = i.conf ? "سري" : "عام";
      const iconClass = fieldIconMap[i.field] || "bi-bookmark-star";

      const shortTxt =
        i.short && i.short.trim()
          ? i.short
          : (i.brief ? (i.brief.substring(0, 80) + "…") : "");

      const detailUrl = prefix + i.id;

      return `
        <div class="card" onclick="location.href='${detailUrl}'">
          <div class="header">
            <div>
              <a class="title" href="${detailUrl}">
                ${i.title || ""}
              </a>
              <p class="name">
                ${typeLabel} • ${i.field || "غير مصنف"} • ${i.year || "-"}
              </p>

              ${
                i.conf
                  ? `<span class="tag-status tag-conf">${statusLabel}</span>`
                  : `<span class="tag-status tag-public">${statusLabel}</span>`
              }
            </div>

            <span class="image">
              <i class="bi ${iconClass}"></i>
            </span>
          </div>

          <p class="description">
            ${shortTxt || ""}
          </p>
        </div>
      `;
    }).join("");

    cardsWrap.innerHTML = html;
  }

  renderCards();
})();
