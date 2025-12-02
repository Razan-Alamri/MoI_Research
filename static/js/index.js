(function () {
  const wrap = document.querySelector(".hero-canvas-wrap");
  if (!wrap || !window.MOCK || !window.MOCK.sectors) return;

  const sectors = window.MOCK.sectors.slice();
  const canvas = document.getElementById("hero3d");
  if (canvas) canvas.style.display = "none";

  const CENTER_SIZE = 160;

  const emirates = sectors.filter(s => s.slug.startsWith("em_"));
  const core = sectors.filter(s => !s.slug.startsWith("em_"));

  const innerCoreCount = Math.min(8, core.length);
  const innerCore = core.slice(0, innerCoreCount);
  const middleCore = core.slice(innerCoreCount);

  function layout() {
    // امسح كل العقد القديمة
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect = wrap.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // 🔹 حجم النود حسب العرض
    let NODE_SIZE;
    if (width >= 1200) {
      NODE_SIZE = 100; // دسكتوب — زي القديم
    } else if (width <= 480) {
      NODE_SIZE = 68;
    } else if (width <= 768) {
      NODE_SIZE = 80;
    } else {
      NODE_SIZE = 90;
    }

    const cx = width / 2;
    const cy = height * 0.49;

    // شعار الوزارة في الوسط
    const centerNode = document.getElementById("moi-center-node");
    if (centerNode) {
      centerNode.style.width = CENTER_SIZE + "px";
      centerNode.style.height = CENTER_SIZE + "px";
      centerNode.style.left = (cx - CENTER_SIZE / 2) + "px";
      centerNode.style.top = (cy - CENTER_SIZE / 2) + "px";
    }

    const padding = 24;
    const distTop = cy;
    const distBottom = height - cy;
    const distLeft = cx;
    const distRight = width - cx;

    const maxRadius =
      Math.min(distTop, distBottom, distLeft, distRight) - (NODE_SIZE / 2) - padding;

    if (maxRadius <= 0) return;

    function drawRing(ring, radiusX, radiusY, offsetRad) {
      const n = ring.length;
      if (!n || radiusX <= 0 || radiusY <= 0) return;

      const step = (2 * Math.PI) / n;

      ring.forEach((sec, i) => {
        const angle = offsetRad + i * step;
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

    // =========================
    // 1) وضع الدسكتوب (زي القديم)
    // =========================
    if (width >= 1200) {
      const ringGap = NODE_SIZE * 1.5;

      const R_OUTER = maxRadius;                 // الحلقة الخارجية
      const R_MID = R_OUTER - ringGap;           // الوسطى
      let R_INNER = R_MID - ringGap;             // الداخلية

      const minInner = (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 7;
      if (R_INNER < minInner) R_INNER = minInner;

      // الداخلية – دائرة كاملة
      drawRing(innerCore, R_INNER, R_INNER, -Math.PI / 2);

      // الوسطى – بيضاوية خفيفة زي ما كانت
      if (middleCore.length) {
        const offsetMid = -Math.PI / 2 + (Math.PI / middleCore.length);
        const middleRadiusY = R_MID * 1.65;
        const middleRadiusX = R_MID * 1.68;
        drawRing(middleCore, middleRadiusX, middleRadiusY, offsetMid);
      }

      // الخارجية – الإمارات
      if (emirates.length) {
        const outerRadiusX = R_OUTER * 1.28;
        const outerRadiusY = R_OUTER * 1.07;
        drawRing(emirates, outerRadiusX, outerRadiusY, -Math.PI / 2);
      }

      return; // نطلع من الفنكشن هنا — ما نطبق وضع الموبايل
    }

    // =========================
    // 2) وضع الشاشات الأصغر (آيباد + جوال)
    // =========================

    const R_OUTER = maxRadius * 0.96;
    const R_MID = R_OUTER * 0.72;

    const minInner = (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 8;
    let R_INNER = R_MID * 0.55;
    if (R_INNER < minInner) R_INNER = minInner;

    // الداخلية
    drawRing(innerCore, R_INNER, R_INNER, -Math.PI / 2);

    // الوسطى
    if (middleCore.length) {
      const offsetMid = -Math.PI / 2 + (Math.PI / middleCore.length);
      const middleRadiusX = R_MID * 0.98;
      const middleRadiusY = R_MID * 0.9;
      drawRing(middleCore, middleRadiusX, middleRadiusY, offsetMid);
    }

    // الخارجية – الإمارات
    if (emirates.length) {
      const outerRadiusX = R_OUTER * 0.98;
      const outerRadiusY = R_OUTER * 0.9;
      drawRing(emirates, outerRadiusX, outerRadiusY, -Math.PI / 2);
    }
  }

  layout();
  document.body.classList.add("hero-ready");

  window.addEventListener("resize", () => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
})();
