/* ==============================================
   HORIZON VOYAGES — RUNTIME CONFIG
   ==============================================
   Environment-specific settings for the frontend. Loaded BEFORE script.js so
   the app reads from window.APP_CONFIG. Swap this one file per environment at
   deploy time — no rebuild needed (this is a static site).

   None of these are secrets:
     • API_KEY is sent in the browser as X-API-Key — it only deters casual
       abuse; real protection is the backend rate limiting + Turnstile.
     • TURNSTILE_SITE_KEY is the *public* Cloudflare key (the secret key lives
       only on the backend).

   For production, set API_BASE to your deployed backend (https://…) and, if you
   switched off the Turnstile test keys, put your real site key here.
*/
window.APP_CONFIG = {
  // Backend API base URL (no trailing slash).
  API_BASE: 'http://localhost:8000',

  // Public API key sent as the X-API-Key header.
  API_KEY: 'dev-secret-key-12345',

  // Cloudflare Turnstile SITE key. Default = official "always passes" TEST key.
  TURNSTILE_SITE_KEY: '1x00000000000000000000AA',
};
