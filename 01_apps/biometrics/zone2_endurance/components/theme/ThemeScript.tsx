/**
 * Anti-FOUC (Flash of Unstyled Content) Theme Initialization Script
 * Injected into the document <head> to synchronously apply the 'dark' class
 * based on localStorage or user system preference before initial DOM paint.
 */
export function ThemeScript() {
  const code = `
    (function() {
      try {
        var storedTheme = localStorage.getItem('theme');
        var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      } catch (e) {
        console.warn('ThemeScript initialization error:', e);
      }
    })();
  `;

  return (
    <script
      id="theme-anti-fouc-script"
      dangerouslySetInnerHTML={{ __html: code }}
    />
  );
}

export default ThemeScript;
