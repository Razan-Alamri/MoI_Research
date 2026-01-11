document.addEventListener("DOMContentLoaded", function () {
  const toggleBtn = document.querySelector(".search-toggle");
  const searchForm = document.querySelector(".global-search");
  const searchInput = searchForm?.querySelector("input");

  if (!toggleBtn || !searchForm) return;

  function openSearch() {
    searchForm.classList.add("is-open");
    setTimeout(() => searchInput && searchInput.focus(), 50);
  }

  function closeSearch() {
    searchForm.classList.remove("is-open");
  }

  toggleBtn.addEventListener("click", () => {
    if (searchForm.classList.contains("is-open")) {
      closeSearch();
    } else {
      openSearch();
    }
  });

  // إغلاق عند الضغط خارج
  document.addEventListener("click", (e) => {
    if (
      !searchForm.contains(e.target) &&
      !toggleBtn.contains(e.target)
    ) {
      closeSearch();
    }
  });
});
