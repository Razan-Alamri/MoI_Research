(function () {
  const wrap = document.querySelector(".hero-canvas-wrap");
  if (!wrap || !window.MOCK || !window.MOCK.sectors) return;

  const sectors = window.MOCK.sectors.slice();
  const canvas = document.getElementById("hero3d");
  if (canvas) canvas.style.display = "none";

  const NODE_SIZE = 100;   // حجم جميع الشعارات
  const CENTER_SIZE = 160; // حجم شعار الوزارة

  const emirates = sectors.filter(s => s.slug.startsWith("em_"));
  const core = sectors.filter(s => !s.slug.startsWith("em_"));

  const innerCoreCount = Math.min(8, core.length);
  const innerCore = core.slice(0, innerCoreCount);
  const middleCore = core.slice(innerCoreCount);

  function layout() {
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect = wrap.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    const cx = width / 2;
    const cy = height * 0.49;

    // شعار الوزارة
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

    const maxRadius = Math.min(distTop, distBottom, distLeft, distRight)
      - (NODE_SIZE / 2) - padding;

    const ringGap = NODE_SIZE * 1.5;

    const R_OUTER = maxRadius;
    const R_MID = R_OUTER - ringGap;

    const minInner = (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 7;
    let R_INNER = R_MID - ringGap;
    if (R_INNER < minInner) R_INNER = minInner;

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

    // الحلقة الداخلية – دائرة كاملة
    drawRing(innerCore, R_INNER, R_INNER, -Math.PI / 2);

    // الحلقة الوسطى
    if (middleCore.length) {
      const offsetMid = -Math.PI / 2 + (Math.PI / middleCore.length);
      const middleRadiusY = R_MID * 1.65;
      const middleRadiusX = R_MID * 1.68;
      drawRing(middleCore, middleRadiusX, middleRadiusY, offsetMid);
    }

    // الحلقة الخارجية – إمارات المناطق
    const outerRadiusX = R_OUTER * 1.28;
    const outerRadiusY = R_OUTER * 1.07;
    if (emirates.length) {
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
