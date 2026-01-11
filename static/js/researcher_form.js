document.addEventListener("DOMContentLoaded", () => {
  // -----------------------------
  // عدّاد الوصف المختصر + الملخص
  // -----------------------------
  const shortInput = document.getElementById("short_desc");
  const shortCounter = document.getElementById("shortCounter");
  const abstractInput = document.getElementById("abstract");
  const abstractCounter = document.getElementById("abstractCounter");

  function updateShort() {
    if (!shortInput || !shortCounter) return;
    const len = shortInput.value.trim().length;
    shortCounter.textContent = `${len} / 220 حرف`;
  }

  function updateAbstract() {
    if (!abstractInput || !abstractCounter) return;
    const len = abstractInput.value.trim().length;
    abstractCounter.textContent = `${len} حرف`;
  }

  if (shortInput) {
    shortInput.addEventListener("input", updateShort);
    updateShort();
  }

  if (abstractInput) {
    abstractInput.addEventListener("input", updateAbstract);
    updateAbstract();
  }

  // لو الباحث اختار قطاعه، نستخدمه كقطاع البحث تلقائيًا إذا حقل البحث فاضي
  const projectSector = document.getElementById("sector");
  const authorSector = document.getElementById("author_sector");

  if (authorSector && projectSector) {
    authorSector.addEventListener("change", () => {
      if (!projectSector.value) {
        projectSector.value = authorSector.value;
      }
    });
  }

  // -----------------------------
  // الباحثون المشاركون (دَيناميك)
  // -----------------------------
  const container = document.getElementById("authorsContainer");
  const template = document.getElementById("authorTemplate");
  const addBtn = document.getElementById("addAuthorBtn");

  // نحسب أكبر index موجود حالياً (مهم في وضع "تعديل")
  let authorIndex = 0;
  if (container) {
    const existingInputs = container.querySelectorAll("[name^='coauthors[']");
    existingInputs.forEach((input) => {
      const m = input.name.match(/^coauthors\[(\d+)\]\[/);
      if (m) {
        const idx = parseInt(m[1], 10);
        if (!Number.isNaN(idx) && idx >= authorIndex) {
          authorIndex = idx + 1;
        }
      }
    });
  }

  if (container && template && addBtn) {
    addBtn.addEventListener("click", () => {
      const clone = template.content.cloneNode(true);

      // 👈 استبدال __NAME__ بـ coauthors[0], coauthors[1] ...
      clone.querySelectorAll("[name]").forEach((input) => {
        input.name = input.name.replace("__NAME__", `coauthors[${authorIndex}]`);
      });

      // زر الإزالة
      const removeBtn = clone.querySelector(".removeAuthorBtn");
      if (removeBtn) {
        removeBtn.addEventListener("click", (e) => {
          e.preventDefault();
          const block = e.target.closest(".author-item");
          if (block) block.remove();
        });
      }

      container.appendChild(clone);
      authorIndex++;
      // بعد الإضافة، نعيد تهيئة "جهة خارجية" لو احتجنا
      initExternalSectorForAll();
    });
  }

  // -----------------------------
  // إظهار حقل "جهة خارجية" عند اختيار other
  // -----------------------------

  function initExternalSectorForAll() {
    // نمر على كل select للمجال (sector) لضبط حالة حقل الجهة الخارجية
    document
      .querySelectorAll("select[name$='[sector]']")
      .forEach((select) => {
        const item = select.closest(".author-item");
        if (!item) return;
        const input = item.querySelector(".external-sector");
        if (!input) return;

        if (select.value === "other") {
          input.style.display = "block";
          input.required = true;
        } else {
          input.style.display = "none";
          input.required = false;
        }
      });
  }

  // تشغيلها مبدئياً للباحثين الموجودين (في وضع تعديل)
  initExternalSectorForAll();

  // أي تغيير في الـ select
  document.addEventListener("change", function (e) {
    if (e.target.matches("select[name$='[sector]']")) {
      const item = e.target.closest(".author-item");
      if (!item) return;
      const input = item.querySelector(".external-sector");
      if (!input) return;

      if (e.target.value === "other") {
        input.style.display = "block";
        input.required = true;
      } else {
        input.style.display = "none";
        input.required = false;
        input.value = "";
      }
    }
  });
});
