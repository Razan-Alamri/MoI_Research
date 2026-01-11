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

  const clamp = (n, a, b) => Math.max(a, Math.min(b, n));

  // تقريب محيط القطع الناقص (Ramanujan)
  function ellipsePerimeter(a, b) {
    const h = Math.pow(a - b, 2) / Math.pow(a + b, 2);
    return Math.PI * (a + b) * (1 + (3 * h) / (10 + Math.sqrt(4 - 3 * h)));
  }

  function drawRing(list, rx, ry, offsetRad, NODE_SIZE) {
    const n = list.length;
    if (!n) return;

    const step = (2 * Math.PI) / n;
    list.forEach((sec, i) => {
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
      node.addEventListener("click", () => (window.location.href = "/sector/" + sec.slug));
      wrap.appendChild(node);
    });
  }

  function drawRingSmart(list, rx, ry, offsetRad, NODE_SIZE, ringGap) {
    const n = list.length;
    if (!n) return;

    const peri = ellipsePerimeter(rx, ry);
    const need = n * (NODE_SIZE + 14); // 14 = فراغ آمن بين النودز

    // إذا المحيط ما يكفي → قسمها حلقتين تلقائيًا
    if (peri < need && n > 10) {
      const half = Math.ceil(n / 2);
      const a = list.slice(0, half);
      const b = list.slice(half);

      drawRing(a, rx, ry, offsetRad, NODE_SIZE);
      drawRing(b, rx - ringGap, ry - ringGap, offsetRad + Math.PI / n, NODE_SIZE);
      return;
    }

    drawRing(list, rx, ry, offsetRad, NODE_SIZE);
  }

  let cx = 0, cy = 0;

  function layout() {
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect = wrap.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    if (width < 60 || height < 60) return;

    const aspect = width / height;

    // ✅ حجم العقدة: يقل تدريجيًا على الشاشات الأصغر
    let NODE_SIZE = 96;
    if (width >= 1400) NODE_SIZE = 102;
    else if (width >= 1200) NODE_SIZE = 96;    // دسكتوب ممتاز
    else if (width >= 992) NODE_SIZE = 88;     // لابتوب
    else if (width >= 768) NODE_SIZE = 78;     // تابلت
    else NODE_SIZE = 68;                       // جوال

    // لو عدد كبير جدًا صغّري أكثر
    const total = innerCore.length + middleCore.length + emirates.length;
    if (total >= 26) NODE_SIZE = Math.max(62, NODE_SIZE - 8);

    cx = width / 2;
    cy = height * 0.49;

    // مركز الشعار
    const centerNode = document.getElementById("moi-center-node");
    if (centerNode) {
      centerNode.style.width = CENTER_SIZE + "px";
      centerNode.style.height = CENTER_SIZE + "px";
      centerNode.style.left = (cx - CENTER_SIZE / 2) + "px";
      centerNode.style.top = (cy - CENTER_SIZE / 2) + "px";
    }

    const padding = 26;
    const halfW = (width / 2) - (NODE_SIZE / 2) - padding;
    const halfH = (height / 2) - (NODE_SIZE / 2) - padding;
    if (halfW <= 0 || halfH <= 0) return;

    const ringGap = Math.max(18, Math.round(NODE_SIZE * 0.62));
    const minInner = (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 12;

    // ✅ أهم نقطة: لا نبالغ في "التبييض" (ellipse stretching)
    // نخليه محافظ جدًا عشان ما يصير تكدس يمين/يسار مثل الصورة
    const stretchX = clamp(1 + (aspect - 1) * 0.12, 0.96, 1.10);
    const stretchY = clamp(1 - (aspect - 1) * 0.06, 0.90, 1.03);

    const outRx = halfW * 0.98 * stretchX;
    const outRy = halfH * 0.98 * stretchY;

    const midRx = Math.max(minInner, outRx - ringGap);
    const midRy = Math.max(minInner, outRy - ringGap);

    const inRx  = Math.max(minInner, midRx - ringGap);
    const inRy  = Math.max(minInner, midRy - ringGap);

    // ✅ الرسم (نفس ترتيبك)
    const startInner = -Math.PI / 2;
    const startMid   = -Math.PI / 2 + (middleCore.length ? (Math.PI / middleCore.length) : 0);
    const startOuter = -Math.PI / 2;

    drawRingSmart(innerCore,  inRx,  inRy,  startInner, NODE_SIZE, ringGap);
    drawRingSmart(middleCore, midRx, midRy, startMid,   NODE_SIZE, ringGap);
    drawRingSmart(emirates,   outRx, outRy, startOuter, NODE_SIZE, ringGap);
  }

  layout();

  const ro = new ResizeObserver(() => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
  ro.observe(wrap);
})();
