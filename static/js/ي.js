(function () {
  const wrap = document.querySelector(".hero-canvas-wrap");
  if (!wrap || !window.MOCK || !window.MOCK.sectors) return;

  const sectors = window.MOCK.sectors.slice();
  const canvas  = document.getElementById("hero3d");
  if (canvas) canvas.style.display = "none"; // ما نستخدم الكانفس هنا

  const NODE_SIZE = 150;   // نفس مقاس hero-orbit-node في الـ CSS
  const CENTER_SIZE = 200; // نفس مقاس center-node في الـ CSS

  // نوزّع 8 قطاعات في الحلقة الداخلية والباقي في الخارجية
  function splitRings(list) {
    const innerCount = Math.min(8, list.length);
    return [list.slice(0, innerCount), list.slice(innerCount)];
  }

  function layout() {
    // امسح نود القطاعات القديمة فقط
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect   = wrap.getBoundingClientRect();
    const width  = rect.width;
    const height = rect.height;

    // ✅ مركز النظام: منتصف الهيرو تماماً
    const cx = width  / 2;
    const cy = height / 2;

    // 🔹 نود وزارة الداخلية في الوسط
    const centerNode = document.getElementById("moi-center-node");
    if (centerNode) {
      centerNode.style.left = (cx - CENTER_SIZE / 2) + "px";
      centerNode.style.top  = (cy - CENTER_SIZE / 2) + "px";
    }

    const [innerRing, outerRing] = splitRings(sectors);

    // 🔹 أنصاف الأقطار — ثابتة وتعطي حلقتين مرتبتين
    const base   = Math.min(width, height);
    const innerR = base * 0.23; // الحلقة الداخلية
    const outerR = base * 0.40; // الحلقة الخارجية (أبعد + كاملة)

    function drawRing(ring, radius, offsetAngleRad) {
      const n = ring.length;
      if (!n) return;

      const step = (2 * Math.PI) / n;  // تقسيم 360 درجة بالتساوي

      for (let i = 0; i < n; i++) {
        const sec   = ring[i];
        const angle = offsetAngleRad + i * step;

        // ✅ دائرة كاملة: نفس الـ radius على X و Y
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);

        const node = document.createElement("div");
        node.className = "hero-orbit-node";
        node.style.left = (x - NODE_SIZE / 2) + "px";
        node.style.top  = (y - NODE_SIZE / 2) + "px";

        const img = document.createElement("img");
        img.src = sec.logo;
        img.alt = sec.name;
        node.appendChild(img);

        node.title = sec.name;
        node.addEventListener("click", () => {
          window.location.href = "/sector/" + sec.slug;
        });

        wrap.appendChild(node);
      }
    }

    // الحلقة الداخلية: تبدأ من الأعلى تماماً (فوق شعار الوزارة)
    drawRing(innerRing, innerR, -Math.PI / 2);

    // الحلقة الخارجية: نلفها نصف خطوة عشان تدخل بين فراغات الحلقة الداخلية
    if (outerRing.length) {
      drawRing(outerRing, outerR, -Math.PI / 2 + (Math.PI / outerRing.length));
    }
  }

  layout();

  // إعادة توزيع عند تغيير حجم الشاشة
  window.addEventListener("resize", () => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
})();

شوف هذا افضل شيء توصلت له لكن يبقى من تحت الشعارات تتداخل


(function () {
  const wrap = document.querySelector(".hero-canvas-wrap");
  if (!wrap || !window.MOCK || !window.MOCK.sectors) return;

  const sectors = window.MOCK.sectors.slice();
  const canvas = document.getElementById("hero3d");
  if (canvas) canvas.style.display = "none";

  // 🔹 حجم موحّد لكل القطاعات
  const NODE_SIZE   = 110;  // كل الشعارات
  const CENTER_SIZE = 190;  // شعار الوزارة فقط أكبر

  // 🔹 تقسيم: إمارات + بقية القطاعات
  const emirates = sectors.filter(s => s.slug.startsWith("em_"));
  const core     = sectors.filter(s => !s.slug.startsWith("em_"));

  const innerCoreCount = Math.min(8, core.length);
  const innerCore  = core.slice(0, innerCoreCount);   // الحلقة القريبة
  const middleCore = core.slice(innerCoreCount);      // الحلقة الوسطى

  function layout() {
    // تنظيف
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect   = wrap.getBoundingClientRect();
    const width  = rect.width;
    const height = rect.height;

    const cx = width  / 2;
    const cy = height * 0.49;   // ننزل الدائرة شوي لتحت عشان الهيدر

    // شعار الوزارة في الوسط
    const centerNode = document.getElementById("moi-center-node");
    if (centerNode) {
      centerNode.style.width  = CENTER_SIZE + "px";
      centerNode.style.height = CENTER_SIZE + "px";
      centerNode.style.left   = (cx - CENTER_SIZE / 2) + "px";
      centerNode.style.top    = (cy - CENTER_SIZE / 2) + "px";
    }

    // 🔹 نحسب أكبر نصف قطر ممكن بدون ما أي نود يطلع برا
    const padding = 24; // مسافة آمنة من الحواف
    const distTop    = cy;
    const distBottom = height - cy;
    const distLeft   = cx;
    const distRight  = width - cx;

    const maxRadius = Math.min(distTop, distBottom, distLeft, distRight) - (NODE_SIZE / 2) - padding;

    // ثلاث حلقات كنسب من أكبر نصف قطر
    const R_OUTER = maxRadius;          // إمارات المناطق
    const R_MID   = maxRadius * 0.80;   // بقية القطاعات
    const R_INNER = maxRadius * 0.49;   // القطاعات الأساسية

    function drawRing(ring, radius, offsetRad) {
      const n = ring.length;
      if (!n || radius <= 0) return;

      const step = (2 * Math.PI) / n;

      ring.forEach((sec, i) => {
        const angle = offsetRad + i * step;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);

        const node = document.createElement("div");
        node.className = "hero-orbit-node";
        node.style.width  = NODE_SIZE + "px";
        node.style.height = NODE_SIZE + "px";
        node.style.left   = (x - NODE_SIZE / 2) + "px";
        node.style.top    = (y - NODE_SIZE / 2) + "px";

        const img = document.createElement("img");
        img.src = sec.logo;
        img.alt = sec.name;
        node.appendChild(img);

        node.title = sec.name;
        node.addEventListener("click", () => {
          window.location.href = "/sector/" + sec.slug;
        });

        wrap.appendChild(node);
      });
    }

    // الحلقة الداخلية – قطاعات أساسية
    drawRing(innerCore,  R_INNER, -Math.PI / 2);

    // الحلقة الوسطى – باقي قطاعات الوزارة (مزوحة نص خطوة عشان تدخل بين فراغات الداخلية)
    if (middleCore.length) {
      const offsetMid = -Math.PI / 2 + (Math.PI / middleCore.length);
      drawRing(middleCore, R_MID, offsetMid);
    }

    // الحلقة الخارجية – إمارات المناطق
    if (emirates.length) {
      drawRing(emirates, R_OUTER, -Math.PI / 2);
    }
  }

  layout();

  window.addEventListener("resize", () => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
})();
