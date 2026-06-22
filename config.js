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
  // Backend API base URL (no trailing slash). Production Render service.
  API_BASE: 'https://horizon-voyages-backend.onrender.com',

  // Public API key sent as the X-API-Key header. Must match API_KEY in Render env.
  API_KEY: 'hv-prod-bf15b93cb1d1c60a8e5aeac225823ea0',

  // Cloudflare Turnstile SITE key (public). Pairs with TURNSTILE_SECRET_KEY in the
  // backend. NOTE: add the production hostname(s) (the *.pages.dev URL and any
  // custom domain) to this widget's allowed hostnames in the Cloudflare Turnstile
  // dashboard, otherwise the bot check fails in production.
  TURNSTILE_SITE_KEY: '0x4AAAAAADmBF37X0IN7DiSp',
};
