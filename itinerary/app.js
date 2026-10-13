// Base API endpoint for itinerary lookup (uses APP_CONFIG in prod, localhost in dev)
const API_BASE_URL = (window.APP_CONFIG && window.APP_CONFIG.API_BASE)
  ? window.APP_CONFIG.API_BASE
  : ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : '');

document.addEventListener('DOMContentLoaded', async () => {
  await loadItineraryData();
  renderAll();
  registerServiceWorker();
  checkOnlineStatus();
});

async function loadItineraryData() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token') || params.get('id');
  if (!token) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/itinerary/${encodeURIComponent(token)}`);
    if (res.ok) {
      const liveData = await res.json();
      if (liveData && liveData.booking) {
        window.VOYAGE_DATA = liveData;
        console.log('[Itinerary] Successfully loaded live itinerary from database for token:', token);
      }
    } else {
      console.warn('[Itinerary] Token not found on server, using cached/sample voyage data.');
    }
  } catch (err) {
    console.warn('[Itinerary] Server unavailable or offline, using cached/sample voyage data:', err);
  }
}

function renderAll() {
  initHero();
  initCountdown();
  initDayChips();
  initDaysTimeline();
  initLogistics();
  initSidebar();
  initDocuments();
  initTabs();
  initModalActions();
}

// ── Populate Hero & Quick Summary ──
function initHero() {
  const heroSection = document.getElementById('itineraryHero');
  if (heroSection && VOYAGE_DATA.heroImage) {
    heroSection.style.backgroundImage = `url('${VOYAGE_DATA.heroImage}')`;
  }

  document.getElementById('clientLead').textContent = `Prepared exclusively for ${VOYAGE_DATA.client.leadGuest}`;
  
  // Format title with semantic spans for flawless mobile & desktop typography
  const shipShort = VOYAGE_DATA.booking.ship.split(' (')[0];
  const mainTitlePart = VOYAGE_DATA.title.replace(' Luxury Expedition', '');
  document.getElementById('voyageTitle').innerHTML = `
    <span class="title-main">${mainTitlePart}</span><br />
    <span class="title-expedition">Luxury Expedition</span><br />
    <em class="title-ship">aboard ${shipShort}</em>
  `;

  document.getElementById('voyageSub').innerHTML = `
    <span>${VOYAGE_DATA.booking.cruiseLine}</span> • 
    <span>${VOYAGE_DATA.booking.stateroom.split(' (')[0]}</span> • 
    <span>Conf #${VOYAGE_DATA.booking.confirmation}</span>
  `;

  // Quick Highlights
  document.getElementById('quickDates').textContent = `${VOYAGE_DATA.booking.embarks.date} → ${VOYAGE_DATA.booking.disembarks.date}`;
  document.getElementById('quickShip').textContent = VOYAGE_DATA.booking.ship.split(' (')[0];
  document.getElementById('quickStateroom').textContent = VOYAGE_DATA.booking.stateroom.split(' (')[0];
  document.getElementById('quickEmbarkPort').textContent = VOYAGE_DATA.booking.embarks.port.split(' (')[0];
}

// ── Live Countdown Timer ──
function initCountdown() {
  const targetDate = new Date(VOYAGE_DATA.countdownTarget).getTime();
  const elDays = document.getElementById('cdDays');
  const elHours = document.getElementById('cdHours');
  const elMins = document.getElementById('cdMins');
  const elSecs = document.getElementById('cdSecs');

  function update() {
    const now = new Date().getTime();
    const diff = targetDate - now;

    if (diff <= 0) {
      document.querySelector('.countdown-units').innerHTML = '<span style="color:var(--gold); font-size:1.2rem; font-weight:500;">Bon Voyage! Currently Sailing</span>';
      return;
    }

    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const s = Math.floor((diff % (1000 * 60)) / 1000);

    elDays.textContent = String(d).padStart(2, '0');
    elHours.textContent = String(h).padStart(2, '0');
    elMins.textContent = String(m).padStart(2, '0');
    elSecs.textContent = String(s).padStart(2, '0');
  }

  update();
  setInterval(update, 1000);
}

// ── Render Day Filter Chips ──
function initDayChips() {
  const container = document.getElementById('dayChipsContainer');
  if (!container) return;

  container.innerHTML = '';
  VOYAGE_DATA.days.forEach((day, index) => {
    const chip = document.createElement('button');
    chip.className = `day-chip ${index === 0 ? 'active' : ''}`;
    chip.dataset.dayNum = day.dayNumber;

    chip.innerHTML = `
      <span class="day-chip-num">Day ${day.dayNumber}</span>
      <span class="day-chip-port" title="${day.port}">${day.type === 'Sea Day' ? 'At Sea' : day.port.split(',')[0]}</span>
    `;

    chip.addEventListener('click', () => {
      document.querySelectorAll('.day-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');

      const targetCard = document.getElementById(`day-card-${day.dayNumber}`);
      if (targetCard) {
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        targetCard.style.borderColor = 'var(--gold)';
        setTimeout(() => {
          targetCard.style.borderColor = '';
        }, 1200);
      }
    });

    container.appendChild(chip);
  });
}

// ── Render Day-by-Day Timeline Cards ──
function initDaysTimeline() {
  const listContainer = document.getElementById('daysListContainer');
  if (!listContainer) return;

  listContainer.innerHTML = '';

  VOYAGE_DATA.days.forEach(day => {
    const card = document.createElement('article');
    card.className = 'day-card';
    card.id = `day-card-${day.dayNumber}`;

    // Timeline events HTML
    const eventsHtml = day.schedule.map(ev => `
      <div class="timeline-event">
        <div class="event-dot">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="6"/></svg>
        </div>
        <div class="event-content">
          <div class="event-meta">
            <span class="event-time">${ev.time}</span>
            <span class="event-category-badge">${ev.category}</span>
          </div>
          <h4 class="event-title">${ev.title}</h4>
          <p class="event-desc">${ev.desc}</p>
        </div>
      </div>
    `).join('');

    card.innerHTML = `
      <div class="day-header">
        <div class="day-header-meta">
          <div class="day-badge-wrap">
            <span class="day-number-badge">Day ${day.dayNumber}</span>
            <span class="day-date-str">${day.date}</span>
          </div>
          <h3 class="day-port-name">${day.port}</h3>
        </div>
        <div class="day-stats">
          <span class="stat-chip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>
            ${day.weather}
          </span>
          ${day.arrival !== '—' ? `
            <span class="stat-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              ${day.arrival} – ${day.departure}
            </span>
          ` : `
            <span class="stat-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 15h18l-2 4H5z"/><path d="M12 13V3l7 10M12 6 6 13"/></svg>
              Ocean Cruising
            </span>
          `}
        </div>
      </div>

      <div class="day-body">
        <div class="day-highlight-banner">
          ${day.highlight}
        </div>

        <div class="timeline">
          ${eventsHtml}
        </div>

        <div class="day-footer">
          <div class="dress-code-pill">
            <span>✨ Dress Code:</span>
            <strong>${day.dressCode}</strong>
          </div>
          ${day.tip ? `
            <div class="advisor-tip">
              <span>💡 Advisor Tip:</span> "${day.tip}"
            </div>
          ` : ''}
        </div>
      </div>
    `;

    listContainer.appendChild(card);
  });
}

// ── Render Logistics (Flights, Hotel, Transfers) ──
function initLogistics() {
  // Flights
  const flightsContainer = document.getElementById('flightsList');
  if (flightsContainer && VOYAGE_DATA.logistics.flights) {
    flightsContainer.innerHTML = VOYAGE_DATA.logistics.flights.map(flight => `
      <div class="flight-card">
        <div class="flight-card-header">
          <span class="flight-direction">${flight.direction} • ${flight.airline}</span>
          <span class="flight-conf">Conf: <strong>${flight.confirmation}</strong></span>
        </div>
        <div class="flight-route-display">
          <div class="flight-endpoint">
            <span class="airport-code">${flight.departure.airport.split(' ')[0]}</span>
            <span class="flight-time">${flight.departure.time}</span>
            <span class="flight-terminal">${flight.departure.terminal}</span>
          </div>
          <div class="flight-path-graphic">
            <svg class="flight-icon-plane" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
            </svg>
            <div class="flight-path-line"></div>
            <span style="font-size:0.75rem; color:var(--muted);">${flight.flightNumber}</span>
          </div>
          <div class="flight-endpoint" style="text-align:right;">
            <span class="airport-code">${flight.arrival.airport.split(' ')[0]}</span>
            <span class="flight-time">${flight.arrival.time}</span>
            <span class="flight-terminal">${flight.arrival.terminal}</span>
          </div>
        </div>
        <div class="flight-meta-strip">
          <span>Class: <strong>${flight.cabin}</strong></span>
          <span>Seats: <strong>${flight.seats}</strong></span>
          <span>${flight.notes}</span>
        </div>
      </div>
    `).join('');
  }

  // Hotel
  const hotel = VOYAGE_DATA.logistics.hotel;
  const hotelContainer = document.getElementById('hotelCardWrap');
  if (hotelContainer && hotel) {
    hotelContainer.innerHTML = `
      <div class="hotel-card">
        <div class="hotel-header">
          <div class="section-eyebrow">Pre-Cruise Luxury Stay</div>
          <h3 class="hotel-name">${hotel.name}</h3>
          <p class="hotel-loc">${hotel.location}</p>
        </div>
        <div class="hotel-meta-row" style="display:flex; flex-wrap:wrap; gap:18px; margin-bottom:14px; font-size:0.88rem;">
          <span>Check-in: <strong>${hotel.checkIn}</strong></span>
          <span>Check-out: <strong>${hotel.checkOut}</strong></span>
          <span>Room: <strong>${hotel.roomType}</strong></span>
          <span>Conf: <strong>${hotel.confirmation}</strong></span>
        </div>
        <div class="hotel-perks-grid">
          ${hotel.amenities.map(perk => `
            <div class="perk-item">
              <span style="color:var(--gold);">✦</span>
              <span>${perk}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Transfers
  const transferContainer = document.getElementById('transfersList');
  if (transferContainer && VOYAGE_DATA.logistics.transfers) {
    transferContainer.innerHTML = VOYAGE_DATA.logistics.transfers.map(tr => `
      <div style="background:var(--navy-card); border:1px solid var(--gold-border); border-radius:var(--radius-sm); padding:16px 20px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
          <div style="font-size:0.75rem; color:var(--gold); text-transform:uppercase; letter-spacing:0.1em;">${tr.date} • ${tr.time}</div>
          <div style="font-size:0.95rem; font-weight:500; color:var(--white);">${tr.service}</div>
          <div style="font-size:0.82rem; color:var(--muted);">${tr.driverDetails}</div>
        </div>
        <span style="font-size:0.75rem; color:var(--green); background:rgba(74,222,128,0.1); padding:4px 10px; border-radius:999px;">Confirmed VIP</span>
      </div>
    `).join('');
  }
}

// ── Sidebar Advisor & Inclusions ──
function initSidebar() {
  const advisor = VOYAGE_DATA.advisor;
  document.getElementById('advisorName').textContent = advisor.name;
  document.getElementById('advisorAgency').textContent = advisor.agency;
  document.getElementById('advisorAvatar').src = advisor.avatar;

  const btnCall = document.getElementById('btnAdvisorCall');
  if (btnCall) btnCall.href = `tel:${advisor.phone}`;
  const btnEmail = document.getElementById('btnAdvisorEmail');
  if (btnEmail) btnEmail.href = `mailto:${advisor.email}?subject=Question regarding voyage ${VOYAGE_DATA.id}`;

  // Amenities
  const amenitiesList = document.getElementById('amenitiesList');
  if (amenitiesList) {
    amenitiesList.innerHTML = VOYAGE_DATA.booking.amenitiesIncluded.map(amenity => `
      <li class="amenity-item">
        <span class="amenity-check">✓</span>
        <span>${amenity}</span>
      </li>
    `).join('');
  }
}

// ── Render Documents & Vault ──
function initDocuments() {
  const container = document.getElementById('documentsVault');
  if (!container) return;

  container.innerHTML = VOYAGE_DATA.documents.map(doc => `
    <div class="doc-card">
      <div class="doc-info">
        <h4>${doc.name}</h4>
        <p>${doc.status || doc.policyNumber || doc.reference || 'On File'}</p>
      </div>
      <button class="doc-btn" onclick="alert('Accessing secure digital document: ${doc.name}')" title="View Document">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      </button>
    </div>
  `).join('');
}

// ── Navigation Tabs ──
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetId = tab.dataset.target;
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ── Modal Actions (Print, Share) ──
function initModalActions() {
  const shareBtn = document.getElementById('btnShareItinerary');
  const shareModal = document.getElementById('shareModal');
  const closeModal = document.getElementById('closeShareModal');
  const copyBtn = document.getElementById('btnCopyShareLink');
  const shareInput = document.getElementById('shareInput');

  if (shareBtn && shareModal) {
    shareBtn.addEventListener('click', () => {
      shareInput.value = window.location.href;
      shareModal.classList.add('active');
    });

    closeModal.addEventListener('click', () => {
      shareModal.classList.remove('active');
    });

    shareModal.addEventListener('click', (e) => {
      if (e.target === shareModal) shareModal.classList.remove('active');
    });

    copyBtn.addEventListener('click', () => {
      shareInput.select();
      navigator.clipboard.writeText(shareInput.value).then(() => {
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = 'Copy Link'; }, 2000);
      });
    });
  }

  // Print Action
  const printBtn = document.getElementById('btnPrintItinerary');
  if (printBtn) {
    printBtn.addEventListener('click', () => {
      window.print();
    });
  }
}

// ── Service Worker & Offline Capability ──
function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js')
      .then(() => console.log('[Horizon Itinerary] Offline ServiceWorker active.'))
      .catch(err => console.log('[Horizon Itinerary] SW registration failed:', err));
  }
}

function checkOnlineStatus() {
  const statusEl = document.getElementById('offlineBadge');
  function updateStatus() {
    if (navigator.onLine) {
      if (statusEl) statusEl.innerHTML = '<span class="status-dot"></span><span class="badge-offline-txt">Offline Ready</span>';
    } else {
      if (statusEl) statusEl.innerHTML = '<span class="status-dot" style="background:#eab308; box-shadow:0 0 8px #eab308;"></span><span class="badge-offline-txt">Sailing Offline</span>';
    }
  }

  window.addEventListener('online', updateStatus);
  window.addEventListener('offline', updateStatus);
  updateStatus();
}
