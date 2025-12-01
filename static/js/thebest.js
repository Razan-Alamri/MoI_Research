(function () {
  const wrap = document.querySelector(".hero-canvas-wrap");
  if (!wrap || !window.MOCK || !window.MOCK.sectors) return;

  const sectors = window.MOCK.sectors.slice();
  const canvas = document.getElementById("hero3d");
  if (canvas) canvas.style.display = "none";

  // 🔹 حجم موحّد لكل القطاعات
  const NODE_SIZE = 110;   // كل الشعارات
  const CENTER_SIZE = 190; // شعار الوزارة فقط أكبر

  // 🔹 تقسيم: إمارات + بقية القطاعات
  const emirates = sectors.filter(s => s.slug.startsWith("em_"));
  const core = sectors.filter(s => !s.slug.startsWith("em_"));

  const innerCoreCount = Math.min(8, core.length);
  const innerCore = core.slice(0, innerCoreCount);   // الحلقة القريبة من الشعار
  const middleCore = core.slice(innerCoreCount);      // الحلقة الوسطى

  function layout() {
    // تنظيف أي عناصر قديمة
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect = wrap.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    const cx = width / 2;
    const cy = height * 0.49;   // ننزل الدائرة شوي لتحت عشان الهيدر

    // شعار الوزارة في الوسط
    const centerNode = document.getElementById("moi-center-node");
    if (centerNode) {
      centerNode.style.width = CENTER_SIZE + "px";
      centerNode.style.height = CENTER_SIZE + "px";
      centerNode.style.left = (cx - CENTER_SIZE / 2) + "px";
      centerNode.style.top = (cy - CENTER_SIZE / 2) + "px";
    }

    // 🔹 نحسب أكبر نصف قطر ممكن بدون ما أي نود يطلع برا
    const padding = 24; // مسافة آمنة من الحواف
    const distTop = cy;
    const distBottom = height - cy;
    const distLeft = cx;
    const distRight = width - cx;

    const maxRadius = Math.min(distTop, distBottom, distLeft, distRight)
      - (NODE_SIZE / 2) - padding;

    // مسافة آمنة بين الحلقات
    const ringGap = NODE_SIZE * 1.5;

    const R_OUTER = maxRadius;
    const R_MID = R_OUTER - ringGap;

    const minInner = (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 7;
    let R_INNER = R_MID - ringGap;
    if (R_INNER < minInner) {
      R_INNER = minInner;
    }

    function drawRing(ring, radiusX, radiusY, offsetRad) {
      const n = ring.length;
      if (!n || radiusX <= 0 || radiusY <= 0) return;

      const step = (2 * Math.PI) / n;

      ring.forEach((sec, i) => {
        const angle = offsetRad + i * step;

        // بيضاوي: نصف قطر أفقي (X) وعمودي (Y)
        const x = cx + radiusX * Math.cos(angle);
        const y = cy + radiusY * Math.sin(angle);

        const node = document.createElement("div");
        node.className = "hero-orbit-node";
        node.style.width = NODE_SIZE + "px";
        node.style.height = NODE_SIZE + "px";
        node.style.left = (x - NODE_SIZE / 2) + "px";
        node.style.top = (y - NODE_SIZE / 2) + "px";

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

    // 🔸 الحلقة الداخلية – دائرية وثابتة حول الشعار
    drawRing(innerCore, R_INNER, R_INNER, -Math.PI / 2);

    // 🔸 الحلقة الوسطى – بيضاوية (أعرض أفقياً وأقل عمقاً عمودياً)
    if (middleCore.length) {
      const offsetMid = -Math.PI / 2 + (Math.PI / middleCore.length);
      const middleRadiusX = R_MID * 2.2; // توسّع أفقي
      const middleRadiusY = R_MID * 1.7; // تقلّص بسيط عمودي لتظهر كبيضاوي
      drawRing(middleCore, middleRadiusX, middleRadiusY, offsetMid);
    }

    // 🔸 الحلقة الخارجية – إمارات المناطق (بيضاوية + أوسع)
    const outerRadiusX = R_OUTER * 1.45;
    const outerRadiusY = R_OUTER * 1.07;

    if (emirates.length) {
      drawRing(emirates, outerRadiusX, outerRadiusY, -Math.PI / 2);
    }
  }

  layout();

  window.addEventListener("resize", () => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
})();