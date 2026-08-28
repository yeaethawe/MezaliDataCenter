(function () {
    const themeKey = 'mezali-dark-theme';

    function readDarkPreference() {
        const stored = localStorage.getItem(themeKey);
        if (stored === null) {
            localStorage.setItem(themeKey, 'true');
            return true;
        }
        return stored === 'true';
    }

    function applyTheme(enabled) {
        document.documentElement.setAttribute('data-bs-theme', enabled ? 'dark' : 'light');
        document.body?.classList.toggle('dark-mode', enabled);
        document.querySelectorAll('[data-dark-theme-toggle]').forEach(toggle => {
            toggle.checked = enabled;
        });
    }

    function bindToggles() {
        document.querySelectorAll('[data-dark-theme-toggle]').forEach(toggle => {
            if (toggle.dataset.themeBound === '1') return;
            toggle.dataset.themeBound = '1';
            toggle.addEventListener('change', () => {
                localStorage.setItem(themeKey, toggle.checked ? 'true' : 'false');
                applyTheme(toggle.checked);
            });
        });
    }

    window.applyMezalionsTheme = applyTheme;
    applyTheme(readDarkPreference());
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            applyTheme(readDarkPreference());
            bindToggles();
        });
    } else {
        bindToggles();
    }
})();
