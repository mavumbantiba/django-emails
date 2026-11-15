(function () {
    const root = document.documentElement;
    const themeToggle = document.getElementById("theme-toggle");
    const progress = document.getElementById("page-progress");

    function setTheme(theme) {
        const isDark = theme === "dark";
        root.dataset.theme = isDark ? "dark" : "light";
        themeToggle.textContent = isDark ? "Light mode" : "Dark mode";
        themeToggle.setAttribute("aria-pressed", String(isDark));
    }

    if (themeToggle) {
        setTheme(root.dataset.theme);
        themeToggle.addEventListener("click", function () {
            const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
            localStorage.setItem("kafunjo-theme", nextTheme);
            setTheme(nextTheme);
        });
    }

    if (!progress) {
        return;
    }

    function showProgress() {
        progress.classList.add("is-visible");
    }

    function hideProgress() {
        progress.classList.remove("is-visible");
    }

    document.addEventListener("click", function (event) {
        if (
            event.defaultPrevented
            || event.button !== 0
            || event.metaKey
            || event.ctrlKey
            || event.shiftKey
            || event.altKey
            || !(event.target instanceof Element)
        ) {
            return;
        }

        const link = event.target.closest("a[href]");
        if (!link || link.hasAttribute("download") || (link.target && link.target !== "_self")) {
            return;
        }

        const destination = new URL(link.href, window.location.href);
        if (
            destination.origin === window.location.origin
            && (
                destination.pathname !== window.location.pathname
                || destination.search !== window.location.search
            )
        ) {
            showProgress();
        }
    });

    document.addEventListener("submit", function (event) {
        if (event.defaultPrevented || !(event.target instanceof HTMLFormElement)) {
            return;
        }

        const form = event.target;
        const destination = new URL(form.action || window.location.href, window.location.href);
        if (destination.origin === window.location.origin && (!form.target || form.target === "_self")) {
            showProgress();
        }
    }, true);

    document.body.addEventListener("htmx:beforeRequest", showProgress);
    document.body.addEventListener("htmx:afterRequest", hideProgress);
    document.body.addEventListener("htmx:sendError", hideProgress);
    document.body.addEventListener("htmx:responseError", hideProgress);
    window.addEventListener("pageshow", hideProgress);
    window.addEventListener("beforeunload", showProgress);
})();
