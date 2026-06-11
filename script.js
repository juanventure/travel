/* ==============================================
   HORIZON VOYAGES — SCRIPT
   ============================================== */

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
    const target = document.querySelector(link.getAttribute('href'));
    if (!target) return;
    e.preventDefault();
    const offset = 80;
    const top = target.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior: 'smooth' });
  });
});

// ── Consultation form ──
const form    = document.getElementById('consult-form');
const success = document.getElementById('form-success');
const submitBtn = document.getElementById('form-submit');

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoad = submitBtn.querySelector('.btn-loading');

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

    // Simulate submission
    btnText.hidden = true;
    btnLoad.hidden = false;
    submitBtn.disabled = true;

    await new Promise(r => setTimeout(r, 1500));

    form.hidden = true;
    success.hidden = false;
  });

  // Live field validation reset
  form.querySelectorAll('input, select, textarea').forEach(field => {
    field.addEventListener('input', () => { field.style.borderColor = ''; });
  });
}

// ── Calendly link placeholder ──
const calendlyLink = document.getElementById('calendly-link');
if (calendlyLink) {
  calendlyLink.addEventListener('click', (e) => {
    e.preventDefault();
    // Replace with your actual Calendly URL:
    // window.open('https://calendly.com/your-advisor', '_blank');
    alert('Replace this with your Calendly URL in script.js line ~140');
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
  // Initialize the CruiseChatClient pointing to the local FastAPI dev server
  const chatClient = new CruiseChatClient('http://localhost:8000', 'dev-secret-key-12345');

  chatToggle.addEventListener('click', () => {
    chatWindow.hidden = !chatWindow.hidden;
    if (!chatWindow.hidden) chatInput.focus();
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
      for await (const chunk of chatClient.sendMessage(text)) {
        if (chunk.type === 'thought') {
          thoughtMsg.querySelector('.msg-content').textContent = chunk.content;
        } else if (chunk.type === 'message') {
          thoughtMsg.remove();
          appendMessage(chunk.content, 'ai-msg');
        }
      }
    } catch (err) {
      console.error(err);
      thoughtMsg.remove();
      appendMessage('Sorry, I am having trouble connecting to the backend. Please try again later.', 'ai-msg');
    }
  });
}
