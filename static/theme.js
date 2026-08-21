(function () {
    const themeKey = 'mezali-dark-theme';
    const isDark = localStorage.getItem(themeKey) === 'true';

    function applyTheme(enabled) {
        document.documentElement.setAttribute('data-bs-theme', enabled ? 'dark' : 'light');
        document.body?.classList.toggle('dark-mode', enabled);
        document.querySelectorAll('[data-dark-theme-toggle]').forEach(toggle => {
            toggle.checked = enabled;
        });
    }

    window.applyMezaliTheme = applyTheme;
    applyTheme(isDark);
    document.addEventListener('DOMContentLoaded', () => {
        applyTheme(localStorage.getItem(themeKey) === 'true');
        document.querySelectorAll('[data-dark-theme-toggle]').forEach(toggle => {
            toggle.addEventListener('change', () => {
                localStorage.setItem(themeKey, toggle.checked ? 'true' : 'false');
                applyTheme(toggle.checked);
            });
        });
    });
})();
