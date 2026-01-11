
(function () {
  const wrap = document.querySelector(".hero-canvas-wrap");
  if (!wrap || !window.MOCK || !window.MOCK.sectors) return;

  const sectors = window.MOCK.sectors.slice();
  const canvas = document.getElementById("hero3d");
  if (canvas) canvas.style.display = "none";

  const emirates = sectors.filter(s => String(s.slug || "").startsWith("em_"));
  const core = sectors.filter(s => !String(s.slug || "").startsWith("em_"));

  const innerCoreCount = Math.min(8, core.length);
  const innerCore = core.slice(0, innerCoreCount);
  const middleCore = core.slice(innerCoreCount);

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function ellipseCircumference(a, b) {
    // Ramanujan approximation
    const h = Math.pow((a - b), 2) / Math.pow((a + b), 2);
    return Math.PI * (a + b) * (1 + (3 * h) / (10 + Math.sqrt(4 - 3 * h)));
  }

  function layout() {
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect = wrap.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // ✅ مساحة احتياطية تحت للأزرار + الهينت (خصوصًا مع فوتر ثابت)
    const ACTIONS_SPACE = 110;  // عدليها 90~130 حسب شكل الأزرار عندك
    const TOP_SPACE = 20;
    const usableH = Math.max(240, height - ACTIONS_SPACE - TOP_SPACE);

    // ✅ مركز أعلى شوي على الشاشات القصيرة
    const cx = width / 2;
    const cy = TOP_SPACE + usableH * (width / height >= 1.3 ? 0.46 : 0.49);

    // ✅ نطلع safeX/safeY بدل maxRadius واحد (عشان الإهليج ما يطلع برا)
    const padding = 22;

    const safeX = Math.max(
      0,
      Math.min(cx, width - cx) - padding
    );

    const safeY = Math.max(
      0,
      Math.min(cy, height - cy - ACTIONS_SPACE) - padding
    );

    if (safeX <= 0 || safeY <= 0) return;

    // ✅ حجم النود ديناميكي حسب المساحة وعدد العناصر (هذا أهم شيء لـ ThinkPad)
    const outerCount = emirates.length || 1;

    // “أفضل” Rx/Ry للحلقة الخارجية: نخليها أعرض شوي لكن بدون تجاوز safeY
    const outerRyBase = safeY * 0.92;
    const outerRxBase = safeX * 0.98;

    // احسب أقصى NODE_SIZE يسمح بمحيط كافي (علشان ما تتزاحم)
    const outerC = ellipseCircumference(outerRxBase, outerRyBase);
    const maxNodeFromOuter = (outerC / outerCount) / 1.35; // 1.35 مسافة بين النودات

    // على الوسطى برضه
    const midCount = middleCore.length || 1;
    const midRxBase = outerRxBase * 0.72;
    const midRyBase = outerRyBase * 0.70;
    const midC = ellipseCircumference(midRxBase, midRyBase);
    const maxNodeFromMid = (midC / midCount) / 1.30;

    let NODE_SIZE = Math.floor(Math.min(104, maxNodeFromOuter, maxNodeFromMid));
    NODE_SIZE = clamp(NODE_SIZE, 58, 104);

    // ✅ حجم الشعار الوسطي يتناسب مع NODE_SIZE ومساحة الشاشة
    const centerNode = document.getElementById("moi-center-node");
    const CENTER_SIZE = clamp(Math.round(NODE_SIZE * 1.75), 130, 190);

    if (centerNode) {
      centerNode.style.width = CENTER_SIZE + "px";
      centerNode.style.height = CENTER_SIZE + "px";
      centerNode.style.left = (cx - CENTER_SIZE / 2) + "px";
      centerNode.style.top = (cy - CENTER_SIZE / 2) + "px";
    }

    // ✅ فجوات الحلقات حسب حجم النود
    const gap = Math.max(14, Math.round(NODE_SIZE * 0.75));

    function drawRing(ring, rx, ry, offsetRad) {
      const n = ring.length;
      if (!n || rx <= 0 || ry <= 0) return;

      const step = (2 * Math.PI) / n;

      ring.forEach((sec, i) => {
        const angle = offsetRad + i * step;
        const x = cx + rx * Math.cos(angle);
        const y = cy + ry * Math.sin(angle);

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

    // ✅ حدد radii لكل حلقة بدون ما تتجاوز safeX/safeY
    const outerRx = outerRxBase;
    const outerRy = outerRyBase;

    const midRx = clamp(outerRx - gap * 1.2, 0, outerRx * 0.85);
    const midRy = clamp(outerRy - gap * 1.2, 0, outerRy * 0.85);

    const innerR = clamp(
      Math.min(midRx, midRy) - gap * 1.15,
      (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 10,
      Math.min(midRx, midRy)
    );

    // ✅ ارسم
    drawRing(innerCore, innerR, innerR, -Math.PI / 2);

    if (middleCore.length) {
      // Offset بسيط عشان ما تصف فوق بعض
      const offsetMid = -Math.PI / 2 + (Math.PI / Math.max(1, middleCore.length));
      drawRing(middleCore, midRx, midRy, offsetMid);
    }

    if (emirates.length) {
      drawRing(emirates, outerRx, outerRy, -Math.PI / 2);
    }
  }

  layout();
  document.body.classList.add("hero-ready");

  window.addEventListener("resize", () => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
})();
