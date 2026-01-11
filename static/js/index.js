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

  function clamp(n, a, b) { return Math.max(a, Math.min(b, n)); }

  function layout() {
    // امسح كل العقد القديمة
    wrap.querySelectorAll(".hero-orbit-node").forEach(el => el.remove());

    const rect = wrap.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    if (width < 50 || height < 50) return;

    const aspect = width / height; // >1 يعني عرض

    // 🔹 حجم النود ديناميكي + مضبوط لشاشات لابتوب
    // ThinkPad عادة 1366x768 / 1920x1080 / 1920x1200 => نبي مقاس مريح
    let NODE_SIZE = 92;
    if (width >= 1500) NODE_SIZE = 102;
    else if (width >= 1200) NODE_SIZE = 96;
    else if (width >= 992) NODE_SIZE = 90;
    else if (width >= 768) NODE_SIZE = 82;
    else NODE_SIZE = 70;

    // إذا عدد العقد كبير جدًا، صغّري شوي
    const totalNodes = innerCore.length + middleCore.length + emirates.length;
    if (totalNodes >= 24) NODE_SIZE = Math.max(66, NODE_SIZE - 10);
    if (totalNodes >= 32) NODE_SIZE = Math.max(62, NODE_SIZE - 8);

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

    // ✅ المساحة المتاحة يمين/يسار/فوق/تحت
    const padding = 22;
    const halfW = (width / 2) - (NODE_SIZE / 2) - padding;
    const halfH = (height / 2) - (NODE_SIZE / 2) - padding;

    if (halfW <= 0 || halfH <= 0) return;

    // ✅ فجوة الحلقات تعتمد على NODE_SIZE
    const ringGap = Math.max(16, Math.round(NODE_SIZE * 0.55));

    // ✅ داخلية/وسطى/خارجية: نحددها كنِسَب مع ضمان عدم التصادم مع المركز
    const minInner = (CENTER_SIZE / 2) + (NODE_SIZE / 2) + 10;

    // نصف قطر “مبدئي” للحلقة الخارجية داخل حدود الشاشة (Ellipse rx/ry منفصل)
    // نستخدم 0.96 عشان ما نكسر الأطراف
    const outerRxMax = halfW * 0.96;
    const outerRyMax = halfH * 0.96;

    // ✅ عوامل بيضاويّة ذكية:
    // - إذا الشاشة عريضة: خلي rx أكبر و ry أصغر شوي (عشان ما تنزل تحت/فوق)
    // - إذا الشاشة طولية: العكس
    const rxFactor = clamp(1.0 + (aspect - 1) * 0.22, 0.92, 1.18); // ThinkPad: تقريبًا 1.05~1.12
    const ryFactor = clamp(1.0 - (aspect - 1) * 0.14, 0.82, 1.02);

    // الحلقة الخارجية (الإمارات)
    const R_OUT_RX = outerRxMax * rxFactor;
    const R_OUT_RY = outerRyMax * ryFactor;

    // الحلقة الوسطى (باقي القطاعات) أصغر بمقدار ringGap
    const R_MID_RX = Math.max(minInner, R_OUT_RX - ringGap - NODE_SIZE * 0.25);
    const R_MID_RY = Math.max(minInner, R_OUT_RY - ringGap - NODE_SIZE * 0.25);

    // الحلقة الداخلية أصغر مرة ثانية
    const R_IN_RX = Math.max(minInner, R_MID_RX - ringGap - NODE_SIZE * 0.18);
    const R_IN_RY = Math.max(minInner, R_MID_RY - ringGap - NODE_SIZE * 0.18);

    // ✅ تحكم إضافي لمنع التزاحم:
    // إذا عدد الحلقة كبير، كبّري نصف قطرها قليل ضمن الحدود
    function adjustForCount(rx, ry, count) {
      if (!count) return { rx, ry };
      // تقريب بسيط: كل ما زاد العدد نحتاج محيط أكبر
      const need = Math.min(1.12, 1 + (count / 18) * 0.05);
      const outRx = Math.min(rx * need, outerRxMax);
      const outRy = Math.min(ry * need, outerRyMax);
      return { rx: outRx, ry: outRy };
    }

    const innerAdj = adjustForCount(R_IN_RX, R_IN_RY, innerCore.length);
    const midAdj   = adjustForCount(R_MID_RX, R_MID_RY, middleCore.length);
    const outAdj   = adjustForCount(R_OUT_RX, R_OUT_RY, emirates.length);

    function drawRing(ring, rx, ry, offsetRad) {
      const n = ring.length;
      if (!n || rx <= 0 || ry <= 0) return;

      // خطوة الزاوية
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

    // ✅ زوايا البداية (توزيع أجمل + يقلل تكدّس أعلى الصفحة)
    const startInner = -Math.PI / 2;
    const startMid   = -Math.PI / 2 + (middleCore.length ? (Math.PI / middleCore.length) : 0);
    const startOuter = -Math.PI / 2;

    drawRing(innerCore, innerAdj.rx, innerAdj.ry, startInner);
    if (middleCore.length) drawRing(middleCore, midAdj.rx, midAdj.ry, startMid);
    if (emirates.length) drawRing(emirates, outAdj.rx, outAdj.ry, startOuter);
  }

  layout();
  document.body.classList.add("hero-ready");

  // ✅ أدق من resize (خصوصًا لو الصفحة داخل layout يتغير)
  const ro = new ResizeObserver(() => {
    clearTimeout(window.__layoutTimer);
    window.__layoutTimer = setTimeout(layout, 120);
  });
  ro.observe(wrap);
})();
