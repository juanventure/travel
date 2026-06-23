/* ==============================================
   HORIZON VOYAGES — SCRIPT
   ============================================== */

// ── Backend / integration config ──
// Values come from config.js (window.APP_CONFIG), loaded before this script so
// they can be swapped per environment without touching app code. Fallbacks keep
// the app working if config.js is missing.
const _cfg = window.APP_CONFIG || {};
const API_BASE = _cfg.API_BASE || 'http://localhost:8000';
const API_KEY = _cfg.API_KEY || 'dev-secret-key-12345';
const TURNSTILE_SITE_KEY = _cfg.TURNSTILE_SITE_KEY || '1x00000000000000000000AA';

// ── Navbar scroll effect ──
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

// ── Mobile hamburger ──
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('nav-links');
hamburger.addEventListener('click', () => {
  hamburger.classList.toggle('open');
  navLinks.classList.toggle('mobile-open');
  document.body.style.overflow = navLinks.classList.contains('mobile-open') ? 'hidden' : '';
});
navLinks.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => {
    hamburger.classList.remove('open');
    navLinks.classList.remove('mobile-open');
    document.body.style.overflow = '';
  });
});

// ── Scroll reveal ──
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      // stagger siblings
      const siblings = entry.target.parentElement.querySelectorAll('[data-reveal]');
      let delay = 0;
      siblings.forEach((el, idx) => { if (el === entry.target) delay = idx * 80; });
      setTimeout(() => entry.target.classList.add('visible'), delay);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

document.querySelectorAll('[data-reveal]').forEach(el => revealObserver.observe(el));

// ── Testimonial carousel ──
(function initTestimonials() {
  const track = document.getElementById('testi-track');
  const dotsContainer = document.getElementById('testi-dots');
  if (!track) return;

  const cards = track.querySelectorAll('.testi-card');
  const total = cards.length;
  let current = 0;
  let autoTimer;

  // Build dots
  cards.forEach((_, i) => {
    const dot = document.createElement('button');
    dot.className = 'testi-dot' + (i === 0 ? ' active' : '');
    dot.setAttribute('aria-label', `Go to testimonial ${i + 1}`);
    dot.addEventListener('click', () => goTo(i));
    dotsContainer.appendChild(dot);
  });

  function updateDots() {
    dotsContainer.querySelectorAll('.testi-dot').forEach((d, i) => {
      d.classList.toggle('active', i === current);
    });
  }

  function getVisibleCount() {
    return window.innerWidth <= 768 ? 1 : 2;
  }

  function goTo(index) {
    const visible = getVisibleCount();
    const max = Math.max(0, total - visible);
    current = Math.max(0, Math.min(index, max));
    const cardWidth = cards[0].offsetWidth + 24; // gap = 24px
    track.style.transform = `translateX(-${current * cardWidth}px)`;
    updateDots();
  }

  document.getElementById('testi-prev').addEventListener('click', () => {
    goTo(current - 1);
    resetAuto();
  });
  document.getElementById('testi-next').addEventListener('click', () => {
    goTo(current + 1);
    resetAuto();
  });

  function resetAuto() {
    clearInterval(autoTimer);
    autoTimer = setInterval(() => {
      const visible = getVisibleCount();
      const max = Math.max(0, total - visible);
      goTo(current >= max ? 0 : current + 1);
    }, 5000);
  }

  resetAuto();
  window.addEventListener('resize', () => goTo(current), { passive: true });
})();

// ── Smooth anchor scroll ──
document.querySelectorAll('a[href^="#"]').forEach(link => {
  link.addEventListener('click', e => {
    const href = link.getAttribute('href');
    if (!href || href === '#') return; // bare "#" (e.g. the logo) is not a scroll target
    const target = document.querySelector(href);
    if (!target) return;
    e.preventDefault();
    // Defer one frame so that closing the mobile menu (removing the fixed
    // overlay and releasing the body scroll-lock) settles BEFORE we measure and
    // scroll. Measuring mid-teardown is what made nav links appear dead on mobile.
    requestAnimationFrame(() => {
      const offset = 80;
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });
});

// ── Consultation form ──
const form    = document.getElementById('consult-form');
const success = document.getElementById('form-success');
const submitBtn = document.getElementById('form-submit');
const formError = document.getElementById('form-error');

if (form) {
  // Render the Turnstile bot-protection widget into the form.
  const consultCaptchaEl = document.getElementById('consult-captcha');
  let consultCaptchaToken = null;
  let consultCaptchaWidgetId = null;

  function renderConsultCaptcha() {
    if (consultCaptchaWidgetId !== null || !window.turnstile || !consultCaptchaEl) return;
    consultCaptchaWidgetId = window.turnstile.render(consultCaptchaEl, {
      sitekey: TURNSTILE_SITE_KEY,
      callback: (token) => { consultCaptchaToken = token; },
      'expired-callback': () => { consultCaptchaToken = null; },
      'error-callback': () => { consultCaptchaToken = null; },
    });
  }
  // Turnstile's async script may not be ready when this runs; retry briefly.
  if (window.turnstile) {
    renderConsultCaptcha();
  } else {
    const t = setInterval(() => {
      if (window.turnstile) { renderConsultCaptcha(); clearInterval(t); }
    }, 300);
    setTimeout(() => clearInterval(t), 10000);
  }

  function showFormError(msg) {
    if (!formError) return;
    formError.textContent = msg;
    formError.hidden = false;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoad = submitBtn.querySelector('.btn-loading');
    if (formError) formError.hidden = true;

    // Simple validation
    const required = form.querySelectorAll('[required]');
    let valid = true;
    required.forEach(field => {
      field.style.borderColor = '';
      if (!field.value.trim()) {
        field.style.borderColor = '#e05c5c';
        valid = false;
      }
    });
    if (!valid) return;

    // Email format check
    const emailField = form.querySelector('#email');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailField.value)) {
      emailField.style.borderColor = '#e05c5c';
      return;
    }

    const formData = new FormData(form);
    const payload = {
      fname: formData.get('fname'),
      lname: formData.get('lname'),
      email: formData.get('email'),
      phone: formData.get('phone'),
      destination: formData.get('destination'),
      budget: formData.get('budget'),
      message: formData.get('message'),
      captcha_token: consultCaptchaToken,
    };

    btnText.hidden = true;
    btnLoad.hidden = false;
    submitBtn.disabled = true;

    try {
      const resp = await fetch(`${API_BASE}/api/consultation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        throw new Error(resp.status === 403
          ? 'Please complete the verification challenge and try again.'
          : `Request failed (${resp.status}).`);
      }
      form.hidden = true;
      success.hidden = false;
    } catch (err) {
      console.error(err);
      showFormError(`${err.message || 'Something went wrong.'} Please try again, or email us directly.`);
      btnText.hidden = false;
      btnLoad.hidden = true;
      submitBtn.disabled = false;
      // Reset the (single-use) Turnstile token so the user can retry.
      if (consultCaptchaWidgetId !== null && window.turnstile) {
        window.turnstile.reset(consultCaptchaWidgetId);
        consultCaptchaToken = null;
      }
    }
  });

  // Live field validation reset
  form.querySelectorAll('input, select, textarea').forEach(field => {
    field.addEventListener('input', () => { field.style.borderColor = ''; });
  });
}

// ── Parallax on hero image ──
const heroImg = document.getElementById('hero-img');
if (heroImg) {
  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    if (scrolled < window.innerHeight) {
      heroImg.style.transform = `scale(1) translateY(${scrolled * 0.25}px)`;
    }
  }, { passive: true });
}

// ── Destination card cursor sparkle effect ──
document.querySelectorAll('.dest-card').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top)  / rect.height) * 100;
    card.style.setProperty('--mouse-x', `${x}%`);
    card.style.setProperty('--mouse-y', `${y}%`);
  });
});

// ── AI Chat Widget ──
const chatToggle = document.getElementById('chat-toggle');
const chatWindow = document.getElementById('chat-window');
const chatClose = document.getElementById('chat-close');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatMessages = document.getElementById('chat-messages');

if (chatToggle && chatWindow) {
  // Initialize the CruiseChatClient pointing to the configured backend
  const chatClient = new CruiseChatClient(API_BASE, API_KEY);

  // ── Cloudflare Turnstile bot protection ──
  const captchaEl = document.getElementById('chat-captcha');
  let captchaToken = null;
  let captchaWidgetId = null;
  // Once the first message succeeds, the backend remembers this session (24h),
  // so the bot-check widget is no longer needed and stays hidden.
  let captchaVerified = false;

  function showCaptcha(visible) {
    if (captchaEl) captchaEl.style.display = visible ? '' : 'none';
  }

  function renderCaptcha() {
    if (captchaWidgetId !== null || !window.turnstile || !captchaEl) return;
    captchaWidgetId = window.turnstile.render(captchaEl, {
      sitekey: TURNSTILE_SITE_KEY,
      callback: (token) => {
        captchaToken = token;
        // Human confirmed — let the "Success!" tick show briefly, then collapse
        // the widget so it doesn't clutter the chat.
        setTimeout(() => { if (captchaToken) showCaptcha(false); }, 1000);
      },
      'expired-callback': () => { captchaToken = null; if (!captchaVerified) showCaptcha(true); },
      'error-callback': () => { captchaToken = null; if (!captchaVerified) showCaptcha(true); },
    });
  }

  chatToggle.addEventListener('click', () => {
    chatWindow.hidden = !chatWindow.hidden;
    if (!chatWindow.hidden) {
      chatInput.focus();
      renderCaptcha(); // render lazily the first time the chat opens
    }
  });

  chatClose.addEventListener('click', () => {
    chatWindow.hidden = true;
  });

  const appendMessage = (text, type = 'ai-msg') => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${type}`;
    const contentDiv = document.createElement('div');
    contentDiv.className = 'msg-content';
    contentDiv.textContent = text;
    msgDiv.appendChild(contentDiv);
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  };

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage(text, 'user-msg');
    chatInput.value = '';
    
    const thoughtMsg = appendMessage('Thinking...', 'ai-msg thought-msg');

    try {
      for await (const chunk of chatClient.sendMessage(text, captchaToken)) {
        if (chunk.type === 'thought') {
          thoughtMsg.querySelector('.msg-content').textContent = chunk.content;
        } else if (chunk.type === 'message') {
          thoughtMsg.remove();
          appendMessage(chunk.content, 'ai-msg');
        }
      }
      // First successful exchange verifies this session server-side (remembered
      // for 24h), so the bot-check widget is no longer needed — keep it hidden.
      captchaVerified = true;
      captchaToken = null;
      showCaptcha(false);
    } catch (err) {
      console.error(err);
      thoughtMsg.remove();
      appendMessage('Sorry, I am having trouble connecting to the backend. Please try again later.', 'ai-msg');
      // Not verified yet — restore a fresh challenge so the user can retry.
      if (!captchaVerified && captchaWidgetId !== null && window.turnstile) {
        window.turnstile.reset(captchaWidgetId);
        captchaToken = null;
        showCaptcha(true);
      }
    }
  });
}
