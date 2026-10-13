# Horizon Voyages — Bespoke Digital Itinerary Platform

A luxury, client-facing digital itinerary web application built for **Horizon Voyages**, designed as a complete in-house replacement for third-party tools like **Travefy**.

---

## 🌟 Key Features

1. **Luxury Visual Identity**:
   * Uses Horizon Voyages' signature design system (midnight navy `#060d1f`, champagne gold `#c8a96e`, and Cormorant Garamond typography).
   * Clean, distraction-free interface matching high-end cruise advisory standards.

2. **Interactive Voyage Experience**:
   * **Live Countdown Timer**: Live ticking countdown down to the second until embarkation day.
   * **Quick Voyage Highlights**: Instant view of sailing dates, vessel, stateroom number, and embarkation port.
   * **Day-by-Day Port Timeline**: Filterable day chips allowing guests to jump between days. Shows port times (arrival, all-aboard, departure), local weather forecasts, booked shore excursions, evening dining reservations, and dress codes.
   * **Advisor Tips**: Curated insider tips on every port call from Juan Garcia.

3. **Complete Pre-Cruise & Logistics Hub**:
   * **Flights**: Outbound and return flight routes with departure/arrival airports, times, terminals, seat assignments, and confirmation codes.
   * **Pre-Cruise Hotel**: Luxury hotel bookings with VIP amenities (breakfast, resort credits, late check-out).
   * **Chauffeur & Transfers**: Private driver pickup details, vehicle types, and meeting points.

4. **Document & Voucher Vault**:
   * One-touch access to cruise boarding passes (SeaPass), travel insurance policy numbers, and private excursion vouchers.

5. **At-Sea Offline Guarantee (PWA)**:
   * Equipped with a dedicated `sw.js` (Service Worker) and `manifest.json`.
   * Caches all assets locally so travelers can view their schedule, vouchers, and emergency contacts in the middle of the ocean without paying for ship Wi-Fi or roaming data.

6. **Flawless PDF & Print Export**:
   * Built-in `@media print` stylesheet.
   * Converts dark theme to crisp white/charcoal print formatting for travelers who prefer a physical travel binder.

7. **Direct Advisor Support**:
   * Prominent contact card with one-click direct call and priority message links to Juan Garcia.

---

## 📁 File Structure

```text
itinerary/
├── index.html        # Main client-facing itinerary portal
├── style.css         # Luxury nautical stylesheet & print formatting
├── data.js           # Voyage data model & sample 12-Night Greek Isles cruise
├── app.js            # Controller (rendering, live timer, filters, offline logic)
├── sw.js             # Service Worker for 100% offline access at sea
├── manifest.json     # PWA configuration for Add-to-Home-Screen
├── assets/           # High-resolution cruise and advisor imagery
└── README.md         # Documentation and architecture guide
```

---

## 🚀 How to Run Locally

You can preview the itinerary with any static server or Python's built-in HTTP server:

```powershell
cd itinerary
python -m http.server 8085
```

Then visit:
```
http://localhost:8085
```

---

## 🔮 Backend & AI Integration (Implemented)

1. **PostgreSQL Database Storage (`travel/backend/app/db.py`)**:
   * `itineraries` table storing unique token, voyage metadata, client info, and complete JSON schema.
   * Auto-token generation with secure 16-byte hex tokens (`secrets.token_hex(16)`).
2. **FastAPI Endpoints (`travel/backend/app/itinerary_router.py`)**:
   * `POST /api/itinerary/parse`: Ingests raw confirmation text or PDF extracts (Norwegian, Carnival, Celebrity, etc.), extracts all logistics, and optionally auto-saves to PostgreSQL.
   * `POST /api/itinerary`: Direct JSON persistence and updates.
   * `GET /api/itinerary/{token}`: Public client-facing endpoint for portal retrieval.
   * `GET /api/itinerary/list/all`: Administrative overview of all client voyages.
3. **AI Confirmation Parser (`travel/backend/app/itinerary_parser.py`)**:
   * Dual-engine architecture: Google Gemini 2.5 Flash via LangChain for contextual nuance + high-precision deterministic regex fallback for offline/local environments.
   * Generates valid `VOYAGE_DATA` JSON with countdown timestamps, cabin details, port timelines, flight routes, and document vaults.
4. **Site Copy Updated**:
   * In `travel/index.html`, all third-party itinerary references replaced with bespoke Horizon Voyages Private Guest Portal branding.
