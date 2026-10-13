// Base API endpoint for itinerary lookup (uses APP_CONFIG in prod, localhost in dev, Render fallback)
const API_BASE_URL = (window.APP_CONFIG && window.APP_CONFIG.API_BASE)
  ? window.APP_CONFIG.API_BASE
  : ((window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://horizon-voyages-backend.onrender.com');

// Safe getter for active voyage data model
function getVoyage() {
  if (window.VOYAGE_DATA && typeof window.VOYAGE_DATA === 'object') {
    return window.VOYAGE_DATA;
  }
  if (typeof VOYAGE_DATA !== 'undefined' && VOYAGE_DATA) {
    return VOYAGE_DATA;
  }
  return {};
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

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
        try { VOYAGE_DATA = liveData; } catch (e) {}
        console.log('[Itinerary] Successfully loaded live itinerary from database for token:', token);
      }
    } else {
      console.warn('[Itinerary] Token not found on server (status ' + res.status + '), using cached/sample voyage data.');
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
  const data = getVoyage();
  const heroSection = document.getElementById('itineraryHero');
  if (heroSection && data.heroImage) {
    heroSection.style.backgroundImage = `url('${data.heroImage}')`;
  }

  const clientLead = data.client?.leadGuest || 'Our Valued Guests';
  const clientLeadEl = document.getElementById('clientLead');
  if (clientLeadEl) clientLeadEl.textContent = `Prepared exclusively for ${clientLead}`;
  
  // Format title with semantic spans for flawless mobile & desktop typography
  const ship = data.booking?.ship || 'Luxury Vessel';
  const shipShort = ship.split(' (')[0];
  let mainTitlePart = data.title || 'Curated Cruise Voyage';
  
  // Avoid duplicating "aboard <Ship>"
  const aboardIdx = mainTitlePart.toLowerCase().indexOf(' aboard ');
  if (aboardIdx !== -1) {
    mainTitlePart = mainTitlePart.substring(0, aboardIdx).trim();
  }
  mainTitlePart = mainTitlePart.replace(/luxury expedition/i, '').trim();

  const voyageTitleEl = document.getElementById('voyageTitle');
  if (voyageTitleEl) {
    voyageTitleEl.innerHTML = `
      <span class="title-main">${escapeHtml(mainTitlePart)}</span><br />
      <span class="title-expedition">${escapeHtml(data.tagline || 'Curated Voyage')}</span><br />
      <em class="title-ship">aboard ${escapeHtml(shipShort)}</em>
    `;
  }

  const voyageSubEl = document.getElementById('voyageSub');
  if (voyageSubEl) {
    const cruiseLine = data.booking?.cruiseLine || '';
    const stateroom = (data.booking?.stateroom || 'Confirmed Cabin').split(' (')[0];
    const conf = data.booking?.confirmation ? `Conf #${data.booking.confirmation}` : 'Confirmed Booking';
    voyageSubEl.innerHTML = `
      <span>${escapeHtml(cruiseLine)}</span> • 
      <span>${escapeHtml(stateroom)}</span> • 
      <span>${escapeHtml(conf)}</span>
    `;
  }

  // Quick Highlights
  const embarks = data.booking?.embarks || {};
  const disembarks = data.booking?.disembarks || {};
  const dateStr = embarks.date && disembarks.date 
    ? `${embarks.date} → ${disembarks.date}` 
    : (embarks.date || disembarks.date || 'Upcoming Sailing');
  
  const quickDatesEl = document.getElementById('quickDates');
  if (quickDatesEl) quickDatesEl.textContent = dateStr;
  
  const quickShipEl = document.getElementById('quickShip');
  if (quickShipEl) quickShipEl.textContent = shipShort;
  
  const quickStateroomEl = document.getElementById('quickStateroom');
  if (quickStateroomEl) quickStateroomEl.textContent = (data.booking?.stateroom || 'Confirmed Cabin').split(' (')[0];
  
  const quickEmbarkPortEl = document.getElementById('quickEmbarkPort');
  if (quickEmbarkPortEl) quickEmbarkPortEl.textContent = (embarks.port || 'Embarkation Port').split(' (')[0];
}

// ── Live Countdown Timer ──
function initCountdown() {
  const data = getVoyage();
  const targetDateStr = data.countdownTarget || data.booking?.embarks?.date;
  if (!targetDateStr) return;

  const targetDate = new Date(targetDateStr).getTime();
  const elDays = document.getElementById('cdDays');
  const elHours = document.getElementById('cdHours');
  const elMins = document.getElementById('cdMins');
  const elSecs = document.getElementById('cdSecs');
  let timerId = null;

  function update() {
    const now = new Date().getTime();
    const diff = targetDate - now;

    if (diff <= 0) {
      const unitsEl = document.querySelector('.countdown-units');
      if (unitsEl) {
        unitsEl.innerHTML = '<span style="color:var(--gold); font-size:1.1rem; font-weight:500;">Bon Voyage! Voyage in Progress / Concluded</span>';
      }
      if (timerId) clearInterval(timerId);
      return;
    }

    const d = Math.floor(diff / (1000 * 60 * 60 * 24));
    const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const s = Math.floor((diff % (1000 * 60)) / 1000);

    if (elDays) elDays.textContent = String(d).padStart(2, '0');
    if (elHours) elHours.textContent = String(h).padStart(2, '0');
    if (elMins) elMins.textContent = String(m).padStart(2, '0');
    if (elSecs) elSecs.textContent = String(s).padStart(2, '0');
  }

  update();
  timerId = setInterval(update, 1000);
}

// ── Render Day Filter Chips ──
function initDayChips() {
  const data = getVoyage();
  const container = document.getElementById('dayChipsContainer');
  if (!container || !Array.isArray(data.days)) return;

  container.innerHTML = '';
  data.days.forEach((day, index) => {
    const chip = document.createElement('button');
    chip.className = `day-chip ${index === 0 ? 'active' : ''}`;
    chip.dataset.dayNum = day.dayNumber;

    const portName = (day.type === 'Sea Day' || !day.port || day.port === 'At Sea') 
      ? 'At Sea' 
      : (day.port.split(',')[0] || day.port);

    chip.innerHTML = `
      <span class="day-chip-num">Day ${day.dayNumber}</span>
      <span class="day-chip-port" title="${escapeHtml(day.port || '')}">${escapeHtml(portName)}</span>
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
  const data = getVoyage();
  const listContainer = document.getElementById('daysListContainer');
  if (!listContainer || !Array.isArray(data.days)) return;

  listContainer.innerHTML = '';

  data.days.forEach(day => {
    const card = document.createElement('article');
    card.className = 'day-card';
    card.id = `day-card-${day.dayNumber}`;

    // Timeline events HTML
    const schedule = Array.isArray(day.schedule) ? day.schedule : [];
    const eventsHtml = schedule.map(ev => `
      <div class="timeline-event">
        <div class="event-dot">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="6"/></svg>
        </div>
        <div class="event-content">
          <div class="event-meta">
            <span class="event-time">${escapeHtml(ev.time || '')}</span>
            <span class="event-category-badge">${escapeHtml(ev.category || 'Cruise')}</span>
          </div>
          <h4 class="event-title">${escapeHtml(ev.title || '')}</h4>
          <p class="event-desc">${escapeHtml(ev.desc || '')}</p>
        </div>
      </div>
    `).join('');

    card.innerHTML = `
      <div class="day-header">
        <div class="day-header-meta">
          <div class="day-badge-wrap">
            <span class="day-number-badge">Day ${day.dayNumber}</span>
            <span class="day-date-str">${escapeHtml(day.date || '')}</span>
          </div>
          <h3 class="day-port-name">${escapeHtml(day.port || '')}</h3>
        </div>
        <div class="day-stats">
          <span class="stat-chip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>
            ${escapeHtml(day.weather || 'Sunny & Pleasant')}
          </span>
          ${(day.arrival && day.arrival !== '—') ? `
            <span class="stat-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              ${escapeHtml(day.arrival)} – ${escapeHtml(day.departure || '')}
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
        ${day.highlight ? `
          <div class="day-highlight-banner">
            ${escapeHtml(day.highlight)}
          </div>
        ` : ''}

        <div class="timeline">
          ${eventsHtml}
        </div>

        <div class="day-footer">
          <div class="dress-code-pill">
            <span>✨ Dress Code:</span>
            <strong>${escapeHtml(day.dressCode || 'Smart Casual')}</strong>
          </div>
          ${day.tip ? `
            <div class="advisor-tip">
              <span>💡 Advisor Tip:</span> "${escapeHtml(day.tip)}"
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
  const data = getVoyage();
  const logistics = data.logistics || {};

  // Flights
  const flightsContainer = document.getElementById('flightsList');
  if (flightsContainer) {
    const flights = Array.isArray(logistics.flights) ? logistics.flights : [];
    if (flights.length > 0) {
      flightsContainer.innerHTML = flights.map(flight => {
        const depCode = (flight.departure?.airport || 'DEP').split(' ')[0];
        const arrCode = (flight.arrival?.airport || 'ARR').split(' ')[0];
        return `
          <div class="flight-card">
            <div class="flight-card-header">
              <span class="flight-direction">${escapeHtml(flight.direction || '')} • ${escapeHtml(flight.airline || '')}</span>
              <span class="flight-conf">Conf: <strong>${escapeHtml(flight.confirmation || 'Confirmed')}</strong></span>
            </div>
            <div class="flight-route-display">
              <div class="flight-endpoint">
                <span class="airport-code">${escapeHtml(depCode)}</span>
                <span class="flight-time">${escapeHtml(flight.departure?.time || '')}</span>
                <span class="flight-terminal">${escapeHtml(flight.departure?.terminal || '')}</span>
              </div>
              <div class="flight-path-graphic">
                <svg class="flight-icon-plane" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
                </svg>
                <div class="flight-path-line"></div>
                <span style="font-size:0.75rem; color:var(--muted);">${escapeHtml(flight.flightNumber || '')}</span>
              </div>
              <div class="flight-endpoint" style="text-align:right;">
                <span class="airport-code">${escapeHtml(arrCode)}</span>
                <span class="flight-time">${escapeHtml(flight.arrival?.time || '')}</span>
                <span class="flight-terminal">${escapeHtml(flight.arrival?.terminal || '')}</span>
              </div>
            </div>
            <div class="flight-meta-strip">
              <span>Class: <strong>${escapeHtml(flight.cabin || 'Standard')}</strong></span>
              <span>Seats: <strong>${escapeHtml(flight.seats || 'Assigned at check-in')}</strong></span>
              <span>${escapeHtml(flight.notes || '')}</span>
            </div>
          </div>
        `;
      }).join('');
    } else {
      flightsContainer.innerHTML = `
        <div style="background:var(--navy-card); border:1px dashed var(--gold-border); border-radius:var(--radius-sm); padding:20px; text-align:center; color:var(--muted); font-size:0.88rem;">
          No air travel booked through agency. Travelers arranging independent transit.
        </div>
      `;
    }
  }

  // Hotel
  const hotel = logistics.hotel;
  const hotelContainer = document.getElementById('hotelCardWrap');
  if (hotelContainer) {
    if (hotel && hotel.name && typeof hotel.name === 'string' && hotel.name.trim() !== '') {
      const amenities = Array.isArray(hotel.amenities) ? hotel.amenities : [];
      const amenitiesHtml = amenities.length > 0
        ? amenities.map(perk => `
            <div class="perk-item">
              <span style="color:var(--gold);">✦</span>
              <span>${escapeHtml(perk)}</span>
            </div>
          `).join('')
        : '<div class="perk-item"><span style="color:var(--gold);">✦</span><span>Confirmed Reservation</span></div>';

      hotelContainer.innerHTML = `
        <div class="hotel-card">
          <div class="hotel-header">
            <div class="section-eyebrow">Pre-Cruise Luxury Stay</div>
            <h3 class="hotel-name">${escapeHtml(hotel.name)}</h3>
            <p class="hotel-loc">${escapeHtml(hotel.location || '')}</p>
          </div>
          <div class="hotel-meta-row" style="display:flex; flex-wrap:wrap; gap:18px; margin-bottom:14px; font-size:0.88rem;">
            <span>Check-in: <strong>${escapeHtml(hotel.checkIn || '—')}</strong></span>
            <span>Check-out: <strong>${escapeHtml(hotel.checkOut || '—')}</strong></span>
            <span>Room: <strong>${escapeHtml(hotel.roomType || 'Standard')}</strong></span>
            <span>Conf: <strong>${escapeHtml(hotel.confirmation || 'Confirmed')}</strong></span>
          </div>
          <div class="hotel-perks-grid">
            ${amenitiesHtml}
          </div>
        </div>
      `;
    } else {
      hotelContainer.innerHTML = `
        <div class="hotel-card" style="padding: 24px; text-align: center; border-style: dashed;">
          <p style="color: var(--muted); font-size: 0.95rem; margin-bottom: 4px;">No pre-cruise hotel stay scheduled on this voyage file.</p>
          <p style="color: var(--gold-light); font-size: 0.82rem;">Direct embarkation at ${escapeHtml(data.booking?.embarks?.port || 'port')}.</p>
        </div>
      `;
    }
  }

  // Transfers
  const transferContainer = document.getElementById('transfersList');
  if (transferContainer) {
    const transfers = Array.isArray(logistics.transfers) ? logistics.transfers : [];
    if (transfers.length > 0) {
      transferContainer.innerHTML = transfers.map(tr => `
        <div style="background:var(--navy-card); border:1px solid var(--gold-border); border-radius:var(--radius-sm); padding:16px 20px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="font-size:0.75rem; color:var(--gold); text-transform:uppercase; letter-spacing:0.1em;">${escapeHtml(tr.date || '')} • ${escapeHtml(tr.time || '')}</div>
            <div style="font-size:0.95rem; font-weight:500; color:var(--white);">${escapeHtml(tr.service || 'Private Chauffeur')}</div>
            <div style="font-size:0.82rem; color:var(--muted);">${escapeHtml(tr.driverDetails || 'Driver details provided prior to arrival')}</div>
          </div>
          <span style="font-size:0.75rem; color:var(--green); background:rgba(74,222,128,0.1); padding:4px 10px; border-radius:999px;">Confirmed VIP</span>
        </div>
      `).join('');
    } else {
      transferContainer.innerHTML = `
        <div style="background:var(--navy-card); border:1px dashed var(--gold-border); border-radius:var(--radius-sm); padding:16px 20px; text-align:center; color:var(--muted); font-size:0.85rem;">
          No private transfers scheduled.
        </div>
      `;
    }
  }
}

// ── Sidebar Advisor & Inclusions ──
function initSidebar() {
  const data = getVoyage();
  const advisor = data.advisor || {};
  const advNameEl = document.getElementById('advisorName');
  if (advNameEl) advNameEl.textContent = advisor.name || 'Juan Garcia';
  const advAgencyEl = document.getElementById('advisorAgency');
  if (advAgencyEl) advAgencyEl.textContent = advisor.agency || 'Horizon Voyages';
  const advAvatarEl = document.getElementById('advisorAvatar');
  if (advAvatarEl && advisor.avatar) advAvatarEl.src = advisor.avatar;

  const advisorEmail = (advisor.email || 'juan@horizonvoyages.net').replace('horizonvoyages.com', 'horizonvoyages.net');
  const btnCall = document.getElementById('btnAdvisorCall');
  if (btnCall && advisor.phone) btnCall.href = `tel:${advisor.phone}`;
  const btnEmail = document.getElementById('btnAdvisorEmail');
  if (btnEmail) btnEmail.href = `mailto:${advisorEmail}?subject=Question regarding voyage ${encodeURIComponent(data.id || '')}`;

  // Amenities
  const amenitiesList = document.getElementById('amenitiesList');
  if (amenitiesList) {
    const amenities = Array.isArray(data.booking?.amenitiesIncluded) ? data.booking.amenitiesIncluded : [];
    if (amenities.length > 0) {
      amenitiesList.innerHTML = amenities.map(amenity => `
        <li class="amenity-item">
          <span class="amenity-check">✓</span>
          <span>${escapeHtml(amenity)}</span>
        </li>
      `).join('');
    } else {
      amenitiesList.innerHTML = `
        <li class="amenity-item">
          <span class="amenity-check">✓</span>
          <span>Complimentary Shipboard Dining &amp; Entertainment</span>
        </li>
      `;
    }
  }
}

// ── Render Documents & Vault ──
function initDocuments() {
  const data = getVoyage();
  const container = document.getElementById('documentsVault');
  if (!container) return;

  const docs = (Array.isArray(data.documents) && data.documents.length > 0)
    ? data.documents
    : [
        {
          name: `${data.booking?.cruiseLine || 'Cruise'} Confirmation Voucher`,
          status: data.booking?.confirmation ? `Conf #${data.booking.confirmation}` : "Confirmed on File",
          type: "Booking Confirmation"
        }
      ];

  container.innerHTML = docs.map(doc => `
    <div class="doc-card">
      <div class="doc-info">
        <h4>${escapeHtml(doc.name || 'Document')}</h4>
        <p>${escapeHtml(doc.status || doc.policyNumber || doc.reference || 'On File')}</p>
      </div>
      <button class="doc-btn" onclick="alert('Accessing secure digital document: ${escapeHtml(doc.name || '')}')" title="View Document">
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
