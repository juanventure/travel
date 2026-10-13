# Host agency switch: Outside Agents → Fora

Status: **website switched to Fora on 2026-10-13** (§1 done: `index.html`,
`terms.html`, `privacy.html`, with the legal pages' "Last updated" dates bumped).
**Still open:** §2 registration numbers (none displayed — don't add one until
Fora confirms it in writing), §3 host-dependent "exclusive" claims, and §4
off-site properties (cruise line portals, Calendly, Travefy, social bios, etc.).
Below, the "Current" columns show the pre-switch Outside Agents wording.

The failure mode to avoid is a gap — a period where the site names a host that
isn't yours yet, or names none at all. Everything here flips on one day.

---

## 0. Before you switch: read your Outside Agents agreement

Ahead of anything on this list, check the OA agreement for:

- **Notice period** for termination, and how notice must be given.
- **What happens to bookings already on the books.** Standard practice across
  host agencies is that a booking made under one host stays with that host
  through sailing and commission payment — you generally cannot move an active
  booking to a new host. If you have clients sailing after the switch date,
  expect to keep servicing them through OA and to receive that commission
  through OA, possibly months later.
- **Post-termination commission.** Confirm in writing that OA pays commission
  on bookings that sail after you leave. This is the single most common way
  advisors lose money in a host switch.
- **Client list / non-solicitation terms**, if any.

Do not start the website changes until you know the answers. The site is the
easy part; the money is in the booking book.

---

## 1. Website changes (8 places)

Every one of these currently reads "Outside Agents". None should change until
switchover day, and all should change on the same day.

### `index.html`

| Line | Current | Notes |
|------|---------|-------|
| 239 | "I'm proudly affiliated with **Outside Agents**, one of North America's leading host agencies, which gives my clients access to exclusive rates, group amenities, and booking support that independent travelers simply can't access." | Rewrite for Fora. Do not carry the "exclusive rates" claim across without checking it is true of your Fora access — see §3. |
| 379 | "Boutique luxury cruise consultancy, proudly affiliated with Outside Agents." | Footer blurb. |
| 419 | "Hosted through **Outside Agents**" | Footer host line. Registration number goes here — see §2. |

### `terms.html`

| Line | Current |
|------|---------|
| 34 | "Horizon Voyages is an independent travel advisory affiliated with the Outside Agents host agency. We help you plan cruises and arrange bookings through Outside Agents and its travel suppliers." |
| 43 | "Bookings are arranged through Outside Agents and the relevant supplier." |
| 67 | "© 2026 Horizon Voyages. Hosted through Outside Agents." |

### `privacy.html`

| Line | Current |
|------|---------|
| 31 | "…is an independent travel advisory affiliated with the Outside Agents host agency." |
| 53 | "**Outside Agents**, our host agency, and the cruise lines and travel suppliers required to research and fulfill your booking" |
| 79 | "© 2026 Horizon Voyages. Hosted through Outside Agents." |

`privacy.html:53` matters more than it looks: it is the disclosure of who your
clients' personal data is shared with. If the host changes and that line does
not, the privacy policy is describing a data flow that no longer happens.

---

## 2. Seller of travel registration

**Fixed 2026-09-09:** the footer previously read "FL Seller of Travel
#ST12345" — a placeholder that was live on the public site. The number has been
removed. Do not put a registration number back until you have a real one.

Several states register sellers of travel and require the registration number
on advertising: **Florida** (FDACS), **California** (CST), **Washington**, and
**Hawaii**. As a hosted advisor you normally operate under the host's
registration rather than your own.

On switchover, ask Fora directly:

- Which of their registration numbers you must display, and in what format.
- Whether their registration covers you in the states where you advertise and
  where your clients live, or whether you need your own.
- Whether they require specific disclosure language identifying them as the
  agency of record.

Get the answer in writing and put the numbers in the footer of all three pages.

---

## 3. Claims that depend on the host

These are true only insofar as your host and its consortium relationships make
them true. Re-check each against what Fora actually gives you before carrying
them over:

- `index.html:153` — "Exclusive amenity packages & upgrades"
- `index.html:180` — "Advisor-exclusive amenities included" (on the Eastern
  Caribbean sample itinerary)
- `index.html:239` — "exclusive rates, group amenities, and booking support
  that independent travelers simply can't access"

Amenity programs are usually tied to specific preferred-partner arrangements
and sometimes to booking volume tiers. A claim that was accurate under OA is
not automatically accurate under Fora.

---

## 4. Everything off the website

The site is the part with version control. These are the ones people forget:

- Email signature and any `@` domain that references the host
- Social bios (Instagram, Facebook, LinkedIn, TikTok)
- Travefy account and itinerary templates/branding
- Calendly booking page description
- Business cards and any printed material
- Google Business Profile description
- Cruise line agent portal registrations — **these are keyed to the host's
  IATA/CLIA number and must be re-registered under Fora's.** CruisingPower,
  GoCCL, First Mates, NCL's portal: each needs your affiliation updated, and
  until it is, bookings may attribute to the wrong agency.
- CLIA individual agent membership, if you hold one
- Any group blocks currently held under OA's IATA — these cannot move; plan
  around them.

---

## 5. Order of operations on the day

1. Fora agreement signed and active; you have their registration numbers and
   disclosure requirements in writing.
2. Re-register on cruise line portals under Fora's IATA/CLIA.
3. Update the three HTML files (§1) and the registration numbers (§2) in one
   commit; push; verify on the live site.
4. Update off-site properties (§4).
5. Keep servicing existing OA bookings through OA until they sail. Do not
   attempt to move them.
