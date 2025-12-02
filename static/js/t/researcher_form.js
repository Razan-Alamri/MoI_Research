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
  let authorIndex = 0;  // المشاركون يبدأون من 0

  const container = document.getElementById("authorsContainer");
  const template = document.getElementById("authorTemplate");
  const addBtn = document.getElementById("addAuthorBtn");

  if (container && template && addBtn) {
    addBtn.addEventListener("click", () => {
      const clone = template.content.cloneNode(true);

      // 👈 هنا التعديل المهم:
      // استبدال __NAME__ بـ coauthors[0], coauthors[1] ...
      clone.querySelectorAll("[name]").forEach(input => {
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
    });
  }



  document.addEventListener("change", function (e) {
    if (e.target.matches("select[name$='[sector]']")) {

      // الحصول على الحقل النصي المقابل
      const input = e.target.closest(".author-item")
        .querySelector(".external-sector");

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
