(function() {
    var storageKey = "aa-theme-preference";
    var themes = {
        light: {
            label: "Light",
            icon: "bi-sun-fill"
        },
        dark: {
            label: "Dark",
            icon: "bi-moon-stars-fill"
        },
        system: {
            label: "System",
            icon: "bi-circle-half"
        }
    };

    var root = document.documentElement;
    var media = typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-color-scheme: dark)")
        : null;

    function isValidPreference(value) {
        return value === "light" || value === "dark" || value === "system";
    }

    function getStoredPreference() {
        var storedPreference = null;

        try {
            storedPreference = window.localStorage.getItem(storageKey);
        } catch (error) {
            storedPreference = null;
        }

        if (isValidPreference(storedPreference)) {
            return storedPreference;
        }

        storedPreference = root.getAttribute("data-theme-preference");
        if (isValidPreference(storedPreference)) {
            return storedPreference;
        }

        return "system";
    }

    function resolveTheme(preference) {
        if (preference === "system") {
            if (media && media.matches) {
                return "dark";
            }
            return "light";
        }

        return preference;
    }

    function updateTrigger(preference, resolvedTheme) {
        var button = document.querySelector("[data-theme-button]");
        var label = document.querySelector("[data-theme-label]");
        var icon = document.querySelector("[data-theme-icon]");

        if (label) {
            label.textContent = themes[preference].label;
        }

        if (icon) {
            icon.className = "bi " + themes[preference].icon;
        }

        if (button) {
            button.setAttribute(
                "title",
                preference === "system"
                    ? "System theme (currently " + resolvedTheme + ")"
                    : themes[preference].label + " theme"
            );
        }
    }

    function updateOptions(preference) {
        var buttons = document.querySelectorAll("[data-theme-value]");

        buttons.forEach(function(button) {
            var isActive = button.getAttribute("data-theme-value") === preference;
            button.classList.toggle("active", isActive);
            button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
    }

    function updateCompactControls(preference, resolvedTheme) {
        var summaries = document.querySelectorAll("[data-theme-summary]");
        var autoButtons = document.querySelectorAll("[data-theme-system-button]");
        var toggleButtons = document.querySelectorAll("[data-theme-toggle]");

        summaries.forEach(function(summary) {
            summary.textContent = preference === "system"
                ? "System (" + themes[resolvedTheme].label + ")"
                : themes[preference].label;
        });

        autoButtons.forEach(function(button) {
            var isSystem = preference === "system";
            button.classList.toggle("active", isSystem);
            button.setAttribute("aria-pressed", isSystem ? "true" : "false");
            button.title = isSystem ? "Following system preference" : "Use system preference";
        });

        toggleButtons.forEach(function(button) {
            var isDark = resolvedTheme === "dark";
            var icon = button.querySelector("[data-theme-toggle-icon]");
            var nextTheme = isDark ? "light" : "dark";

            button.classList.toggle("is-dark", isDark);
            button.setAttribute("aria-pressed", isDark ? "true" : "false");
            button.setAttribute("aria-label", "Switch to " + themes[nextTheme].label.toLowerCase() + " theme");
            button.title = "Switch to " + themes[nextTheme].label + " theme";

            if (icon) {
                icon.className = "bi " + (isDark ? "bi-moon-stars-fill" : "bi-sun-fill");
            }
        });
    }

    function storePreference(preference) {
        try {
            window.localStorage.setItem(storageKey, preference);
        } catch (error) {
            return;
        }
    }

    function applyPreference(preference) {
        var resolvedTheme = resolveTheme(preference);

        root.setAttribute("data-theme-preference", preference);
        root.setAttribute("data-theme-resolved", resolvedTheme);
        root.setAttribute("data-bs-theme", resolvedTheme);

        updateTrigger(preference, resolvedTheme);
        updateOptions(preference);
        updateCompactControls(preference, resolvedTheme);
    }

    function onThemeSelect(event) {
        var preference = event.currentTarget.getAttribute("data-theme-value");

        if (!isValidPreference(preference)) {
            return;
        }

        storePreference(preference);
        applyPreference(preference);
    }

    function onThemeToggle() {
        var preference = getStoredPreference();
        var resolvedTheme = resolveTheme(preference);
        var nextTheme = resolvedTheme === "dark" ? "light" : "dark";

        storePreference(nextTheme);
        applyPreference(nextTheme);
    }

    function onThemeSystem() {
        storePreference("system");
        applyPreference("system");
    }

    function onSystemThemeChange() {
        if (getStoredPreference() === "system") {
            applyPreference("system");
        }
    }

    document.querySelectorAll("[data-theme-value]").forEach(function(button) {
        button.addEventListener("click", onThemeSelect);
    });

    document.querySelectorAll("[data-theme-toggle]").forEach(function(button) {
        button.addEventListener("click", onThemeToggle);
    });

    document.querySelectorAll("[data-theme-system-button]").forEach(function(button) {
        button.addEventListener("click", onThemeSystem);
    });

    applyPreference(getStoredPreference());

    if (media) {
        if (typeof media.addEventListener === "function") {
            media.addEventListener("change", onSystemThemeChange);
        } else if (typeof media.addListener === "function") {
            media.addListener(onSystemThemeChange);
        }
    }
})();