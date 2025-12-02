(function () {
  if (!window.MOCK) return;

  const items = window.MOCK.items || [];
  const sectors = window.MOCK.sectors || [];
  const authorsMap = window.MOCK.authors || {};

  // عناصر DOM
  const sumTotalEl = document.getElementById("sumTotal");
  const sumResearchEl = document.getElementById("sumResearch");
  const sumProjectEl = document.getElementById("sumProject");
  const sumInnovationEl = document.getElementById("sumInnovation");
  const sumAuthorsEl = document.getElementById("sumAuthors");

  const sectorFilterEl = document.getElementById("dashSectorFilter");
  const fieldFilterEl = document.getElementById("dashFieldFilter");

  const ctxSector = document.getElementById("chartBySector");
  const ctxYear = document.getElementById("chartByYear");
  const ctxField = document.getElementById("chartByField");

  if (!ctxSector || !ctxYear || !ctxField) return;
  // 🎨 إعداد الخط الافتراضي والألوان العامة للرسمات
  Chart.defaults.font.family = "'Tajawal', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  Chart.defaults.font.size = 12;

  const cssRoot = getComputedStyle(document.documentElement);
  const chartTextColor = cssRoot.getPropertyValue("--fg")?.trim() || "#111827";

  Chart.defaults.color = chartTextColor;

  // 🔢 بلجن بسيط لإظهار الأرقام فوق الأعمدة/النقاط في الـ bar + line
  const valueLabelsPlugin = {
    id: "valueLabels",
    afterDatasetsDraw(chart, args, pluginOptions) {
      const { ctx } = chart;
      ctx.save();
      ctx.font = "11px Tajawal, system-ui, sans-serif";
      ctx.fillStyle = chartTextColor;
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";

      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);
        if (!meta.hidden) {
          meta.data.forEach((element, index) => {
            const val = dataset.data[index];
            if (val == null) return;

            const pos = element.tooltipPosition();

            ctx.textAlign = "left";
            ctx.textBaseline = "middle";

            // نضع الرقم على يمين البار بفارق 8px
            ctx.fillText(val, pos.x + 8, pos.y);
          });

        }
      });

      ctx.restore();
    }
  };

  Chart.register(valueLabelsPlugin);

  // تعبئة فلتر القطاع
  if (sectorFilterEl) {
    sectors.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.slug;
      opt.textContent = s.name;
      sectorFilterEl.appendChild(opt);
    });
  }

  // تعبئة فلتر المجال من البيانات
  if (fieldFilterEl) {
    const fields = [...new Set(items.map(i => i.field).filter(Boolean))];
    fields.forEach(f => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      fieldFilterEl.appendChild(opt);
    });
  }

  // دالة إرجاع المبادرات حسب الفلاتر
  function getFilteredItems() {
    const s = sectorFilterEl ? sectorFilterEl.value : "";
    const f = fieldFilterEl ? fieldFilterEl.value : "";

    return items.filter(it => {
      let ok = true;
      if (s && it.sector !== s) ok = false;
      if (f && it.field !== f) ok = false;
      return ok;
    });
  }

  // حساب الإحصاءات من قائمة عناصر
  function computeStats(list) {
    const total = list.length;
    const totalResearch = list.filter(i => i.type === "Research").length;
    const totalProject = list.filter(i => i.type === "Project").length;
    const totalInnovation = list.filter(i => i.type === "Innovation").length;

    // عدد الباحثين (حسب authorsMap)
    const authorSet = new Set();
    list.forEach(i => {
      const auths = authorsMap[i.id] || [];
      auths.forEach(a => {
        // نستخدم الإيميل لو موجود، وإلا الاسم
        const key = a.email || a.name;
        if (key) authorSet.add(key);
      });
    });

    return {
      total,
      totalResearch,
      totalProject,
      totalInnovation,
      totalAuthors: authorSet.size
    };
  }

  // توليد بيانات الرسوم من القائمة المفلترة
  function buildChartsData(list) {
    // حسب القطاع
    const bySectorMap = {};
    list.forEach(i => {
      bySectorMap[i.sector] = (bySectorMap[i.sector] || 0) + 1;
    });
    const sectorLabels = [];
    const sectorValues = [];
    Object.keys(bySectorMap).forEach(slug => {
      const sec = sectors.find(s => s.slug === slug);
      sectorLabels.push(sec ? sec.name : slug);
      sectorValues.push(bySectorMap[slug]);
    });

    // حسب السنة
    const byYearMap = {};
    list.forEach(i => {
      const y = i.year || "غير محدد";
      byYearMap[y] = (byYearMap[y] || 0) + 1;
    });
    const yearLabels = Object.keys(byYearMap).sort();
    const yearValues = yearLabels.map(y => byYearMap[y]);

    // حسب المجال
    const byFieldMap = {};
    list.forEach(i => {
      const f = i.field || "غير مصنف";
      byFieldMap[f] = (byFieldMap[f] || 0) + 1;
    });
    const fieldLabels = Object.keys(byFieldMap);
    const fieldValues = fieldLabels.map(f => byFieldMap[f]);

    return {
      sectorLabels,
      sectorValues,
      yearLabels,
      yearValues,
      fieldLabels,
      fieldValues
    };
  }

  // إنشاء الرسوم لأول مرة
  let chartSector, chartYear, chartField;

  function initCharts(data) {
    // ألوان موحّدة للرسمات
    const mainGreen = "#0b7a41";
    const softGreen = "#16a34a";

    // ===== رسم حسب القطاع (Bar) =====
    chartSector = new Chart(ctxSector, {
      type: "bar",
      data: {
        labels: data.sectorLabels,
        datasets: [{
          label: "عدد المبادرات",
          data: data.sectorValues,
          backgroundColor: "#0b7a41",
          borderColor: "#0b7a41",
          borderWidth: 1.5,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",   // 👈 يخلي الأعمدة أفقية
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return `عدد المبادرات: ${ctx.parsed.x}`;
              }
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: {
            top: 10,
            right: 16,
            bottom: 10,
            left: 10
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: "rgba(148, 163, 184, 0.25)" },
            ticks: {
              precision: 0
            }
          },
          y: {
            grid: { display: false },
            ticks: {
              autoSkip: false,
              font: {
                size: 12,
                weight: "500"
              },
              padding: 6
            }

          }
        }
      }
    });

    // ===== رسم حسب السنة (Line) =====
    chartYear = new Chart(ctxYear, {
      type: "line",
      data: {
        labels: data.yearLabels,
        datasets: [{
          label: "إجمالي المبادرات",
          data: data.yearValues,
          tension: 0.25,
          borderColor: mainGreen,
          backgroundColor: "rgba(11, 122, 65, 0.12)",
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: softGreen,
          pointBorderColor: "#ffffff",
          pointBorderWidth: 1.5
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return `إجمالي المبادرات: ${ctx.parsed.y}`;
              }
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: {
            top: 18
          }
        },
        scales: {
          x: {
            grid: { display: false }
          },
          y: {
            beginAtZero: true,
            grid: { color: "rgba(148, 163, 184, 0.25)" },
            ticks: {
              precision: 0,
              padding: 6  // مسافة بسيطة بين الأرقام ومحور y

            }
          }
        }
      }
    });

    // ===== رسم حسب المجال (Doughnut) =====
    chartField = new Chart(ctxField, {
      type: "doughnut",
      data: {
        labels: data.fieldLabels,
        datasets: [{
          data: data.fieldValues,
          backgroundColor: [
            "#006c35", // 1 أخضر وزارة الداخلية
            "#1e3a8a", // 2 أزرق داكن
            "#4caf50", // 3 أخضر متوسط
            "#3b82f6", // 4 أزرق سماوي
            "#1f2937", // 5 رمادي غامق
            "#0f766e", // 6 تركواز داكن
            "#0284c7", // 7 أزرق متوسط
            "#65a30d", // 8 زيتي أخضر
            "#475569", // 9 رمادي أزرق
            "#10b981", // 10 أخضر فيروزي
            "#2563eb", // 11 أزرق ملكي
            "#15803d", // 12 أخضر غامق إضافي
            "#64748b", // 13 رمادي معدني
            "#94a3b8"  // 14 رمادي سماوي فاتح
          ]
        }]
      },
      options: {
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
              pointStyle: "circle",
              boxWidth: 8,
              font: {
                family: "Tajawal, system-ui, sans-serif",
                size: 11
              }
            }
          },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                const label = ctx.label || "";
                const value = ctx.parsed;
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const perc = total ? ((value / total) * 100).toFixed(1) : 0;
                return `${label}: ${value} عنصر (${perc}٪)`;
              }
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false,
        cutout: "55%"
      }
    });
  }


  // تحديث البيانات في الرسوم
  function updateCharts(data) {
    // قطاع
    chartSector.data.labels = data.sectorLabels;
    chartSector.data.datasets[0].data = data.sectorValues;
    chartSector.update();

    // سنة
    chartYear.data.labels = data.yearLabels;
    chartYear.data.datasets[0].data = data.yearValues;
    chartYear.update();

    // مجال
    chartField.data.labels = data.fieldLabels;
    chartField.data.datasets[0].data = data.fieldValues;
    chartField.update();
  }

  // إعادة رسم كل شيء عند تغيير الفلاتر
  function refresh() {
    const filtered = getFilteredItems();
    const stats = computeStats(filtered);
    const chartData = buildChartsData(filtered);

    if (sumTotalEl) sumTotalEl.textContent = stats.total;
    if (sumResearchEl) sumResearchEl.textContent = stats.totalResearch;
    if (sumProjectEl) sumProjectEl.textContent = stats.totalProject;
    if (sumInnovationEl) sumInnovationEl.textContent = stats.totalInnovation;
    if (sumAuthorsEl) sumAuthorsEl.textContent = stats.totalAuthors;

    if (!chartSector || !chartYear || !chartField) {
      initCharts(chartData);
    } else {
      updateCharts(chartData);
    }
  }

  // ربط الفلاتر
  if (sectorFilterEl) sectorFilterEl.addEventListener("change", refresh);
  if (fieldFilterEl) fieldFilterEl.addEventListener("change", refresh);

  // أول مرة
  refresh();
})();
