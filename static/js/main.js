// عناصر عامة مشتركة
document.addEventListener("DOMContentLoaded", () => {
  // شريط KPI في الرئيسية (إذا وُجد)
  const t = document.getElementById("kpiTicker");
  if (t && window.MOCK?.stats?.summary) {
    const s = window.MOCK.stats.summary;
    t.textContent = `إجمالي: ${s.total} • أبحاث: ${s.researches} • مشاريع: ${s.projects} • ابتكارات: ${s.innovations}`;
  }
});
