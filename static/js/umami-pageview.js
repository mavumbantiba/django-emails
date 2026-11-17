(function () {
    const tracker = document.querySelector("[data-umami-tracker]");
    if (!tracker || !window.umami || typeof window.umami.track !== "function") {
        return;
    }

    const pageName = tracker.dataset.pageName;
    const websiteId = tracker.dataset.websiteId;
    if (!pageName || !websiteId) {
        return;
    }

    window.umami.track({
        website: websiteId,
        url: `/page/${encodeURIComponent(pageName)}`,
        title: pageName,
    });
})();
