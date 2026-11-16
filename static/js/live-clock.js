(function () {
    document.querySelectorAll(".live-clock").forEach(function (clock) {
        const formatter = new Intl.DateTimeFormat(undefined, {
            timeZone: clock.dataset.timeZone,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hourCycle: "h23",
        });

        function updateClock() {
            const now = new Date();
            clock.dateTime = now.toISOString();
            clock.textContent = formatter.format(now);
        }

        updateClock();
        window.setInterval(updateClock, 1000);
    });
})();
