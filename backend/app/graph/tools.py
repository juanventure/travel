import json
import os
from datetime import datetime
from typing import Optional

import httpx
from langchain_core.tools import tool

from app.guardrails import scrub_prices, strip_links

# Mock in-memory GDS database
MOCK_GDS = [
    {
        "id": "VOY-123",
        "region": "Caribbean",
        "cruise_line": "Royal Caribbean",
        "ship": "Oasis of the Seas",
        "nights": 7,
        "price_per_person": 1200,
        "date": "2026-11-15"
    },
    {
        "id": "VOY-456",
        "region": "Mediterranean",
        "cruise_line": "Celebrity Cruises",
        "ship": "Edge",
        "nights": 12,
        "price_per_person": 3500,
        "date": "2026-05-10"
    },
    {
        "id": "VOY-789",
        "region": "Alaska",
        "cruise_line": "Holland America",
        "ship": "Koningsdam",
        "nights": 10,
        "price_per_person": 2200,
        "date": "2026-07-20"
    }
]

@tool
def search_gds_inventory(region: Optional[str] = None, max_price: Optional[int] = None) -> str:
    """
    Searches available cruise voyages that suit the guest's request.
    Args:
        region: The destination region (e.g., 'Caribbean', 'Mediterranean', 'Alaska').
        max_price: The guest's approximate per-person budget, used only to narrow
            which sailings to suggest. Fares are NOT returned — pricing changes
            until a deposit is placed and is confirmed later by a human advisor.
    Returns:
        A string formatted list of matching voyages (no pricing).
    """
    results = MOCK_GDS
    
    if region:
        results = [v for v in results if region.lower() in v["region"].lower()]
    
    if max_price:
        results = [v for v in results if v["price_per_person"] <= max_price]
        
    if not results:
        return "No sailings found matching those criteria."
        
    output = "Found the following sailings:\n"
    for v in results:
        output += f"- [{v['id']}] {v['nights']} nights in {v['region']} on {v['cruise_line']} {v['ship']} (sailing {v['date']})\n"
        
    return output

def get_cruise_details(cruise_id: str) -> Optional[str]:
    """Format a one-line summary of a cruise from the mock GDS, or None if unknown."""
    cruise = next((v for v in MOCK_GDS if v["id"].lower() == cruise_id.lower()), None)
    if not cruise:
        return None
    return (f"- [{cruise['id']}] {cruise['nights']} nights in {cruise['region']} "
            f"on {cruise['cruise_line']} {cruise['ship']} (sailing {cruise['date']})")


@tool
def submit_booking_lead(full_name: str, email: str, cruise_id: str,
                        num_passengers: Optional[str] = None,
                        cruise_length: Optional[str] = None,
                        travel_dates: Optional[str] = None) -> str:
    """
    Records a finalized booking lead in the travel agency CRM.
    MUST be called once the user has provided their name, email, and selected a
    cruise. Also pass, whenever the user has shared them:
        num_passengers: how many people are travelling (e.g. '2 adults, 1 child').
        cruise_length: preferred trip length, e.g. '7 nights' or '10-14 nights'.
        travel_dates: preferred dates or date range, e.g. 'early June 2026, +/- 3 days'.
    """
    # Records the lead. The agency is notified by email in the booking node so the
    # (blocking) send runs off the event loop and the confirmation can reflect it.
    print(f"*** NEW BOOKING LEAD: {full_name} ({email}) wants {cruise_id} | "
          f"pax={num_passengers} length={cruise_length} dates={travel_dates} ***")
    return f"Booking lead for {full_name} ({email}) on {cruise_id} has been recorded."


# ---------------------------------------------------------------------------
# Live web search (function calling)
# ---------------------------------------------------------------------------
#
# 1. TOOL SCHEMA — registered with the LLM via `llm.bind_tools([...])`. This is
#    the exact function declaration the model sees; it decides when to call it
#    and fills in the arguments from the guest's message (e.g. "Search for a
#    Caribbean cruise for July 2025" -> destination="Caribbean", month="July",
#    year=2025).
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

SEARCH_LIVE_CRUISES_SCHEMA = {
    "name": "search_live_cruises",
    "description": (
        "Search the live web for real cruise sailings and itineraries for a "
        "destination in a specific month and year. Call this whenever "
        "the guest asks to find, search for or look up cruises. Do not call it "
        "until the destination, month and year are all known."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": (
                    "Cruise region or destination, e.g. 'Caribbean', "
                    "'Mediterranean', 'Alaska', 'Northern Europe'."
                ),
            },
            "month": {
                "type": "string",
                "enum": _MONTH_NAMES,
                "description": "Full English name of the month the guest wants to sail.",
            },
            "year": {
                "type": "integer",
                "description": "Four-digit sailing year, e.g. 2026.",
            },
            "cruise_line": {
                "type": "string",
                "description": (
                    "Optional. Only set if the guest named a cruise line, e.g. "
                    "'Royal Caribbean', 'Celebrity Cruises', 'Virgin Voyages'."
                ),
            },
        },
        "required": ["destination", "month", "year"],
    },
}

TAVILY_URL = "https://api.tavily.com/search"
MAX_RESULTS = 5
SNIPPET_CHARS = 500  # keep tool output small so it doesn't bloat the LLM context

# Online travel agencies and discount cruise sellers: competitors for the sale,
# and their pages are mostly fares + "book now". Override with
# CRUISE_SEARCH_EXCLUDE_DOMAINS (comma-separated). Optionally pin results to
# specific sites with CRUISE_SEARCH_INCLUDE_DOMAINS.
_DEFAULT_EXCLUDE = (
    "expedia.com,kayak.com,priceline.com,travelocity.com,orbitz.com,cheaptickets.com,"
    "cruise.com,cruises.com,cruisedirect.com,vacationstogo.com,cruisesonly.com,"
    "icruise.com,cruiseplum.com,costco.com,cruisecompete.com,cruisesheet.com"
)


def _env_list(name: str, default: str = "") -> list:
    return [d.strip() for d in os.getenv(name, default).split(",") if d.strip()]


_EXCLUDE_DOMAINS = _env_list("CRUISE_SEARCH_EXCLUDE_DOMAINS", _DEFAULT_EXCLUDE)
_INCLUDE_DOMAINS = _env_list("CRUISE_SEARCH_INCLUDE_DOMAINS")


def _error(code: str, message: str) -> str:
    """Errors are returned AS DATA so the LLM can explain them to the guest."""
    return json.dumps({"ok": False, "error": code, "message": message})


# 2. API EXECUTION — runs when the LLM emits a `search_live_cruises` tool call.
async def search_live_cruises(destination: str, month: str, year: int,
                              cruise_line: Optional[str] = None) -> str:
    """
    Call the live search API with the model-extracted parameters and return a
    JSON string: {"ok": true, "query", "results": [{"title","snippet"}]} — no
    URLs and no prices by design (see the PARSE step).
    Never raises — failures come back as {"ok": false, ...}.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("[search] TAVILY_API_KEY not set; live search unavailable.")
        return _error("not_configured", "Live search is not configured right now.")

    # Validate the model's arguments rather than trusting them.
    month_name = next((m for m in _MONTH_NAMES
                       if m.lower() == str(month).strip().lower()), None)
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = None
    if not destination or not month_name or not year:
        return _error("bad_arguments",
                      "Need a destination, a month and a four-digit year.")

    # A sailing in a month that has already ended can't be searched usefully.
    now = datetime.now()
    if (year, _MONTH_NAMES.index(month_name) + 1) < (now.year, now.month):
        return _error("date_in_past",
                      f"{month_name} {year} has already passed. "
                      f"Today is {now:%B %d, %Y}. Ask the guest for a future date.")

    query = " ".join(filter(None, [
        cruise_line, destination, "cruise sailings itinerary", month_name, str(year),
    ]))
    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": MAX_RESULTS,
        "include_answer": False,
        "exclude_domains": _EXCLUDE_DOMAINS,
    }
    if _INCLUDE_DOMAINS:
        payload["include_domains"] = _INCLUDE_DOMAINS
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                TAVILY_URL, json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        print(f"[search] API returned {exc.response.status_code}: {exc.response.text[:200]}")
        return _error("api_error", "The live search service returned an error.")
    except Exception as exc:  # noqa: BLE001 - timeouts, DNS, bad JSON, etc.
        print(f"[search] request failed: {exc!r}")
        return _error("unavailable", "The live search service could not be reached.")

    # 3. PARSE — reduce the raw API response to research the LLM can summarise.
    #    COMMISSION PROTECTION: URLs are deliberately NOT passed to the model. A
    #    third-party booking link would let a guest book around the advisor (no
    #    commission, not tied to Fora's IATA#). Prices are scrubbed too, so fares
    #    can't be relayed. URLs are only logged server-side.
    results = []
    for r in data.get("results", [])[:MAX_RESULTS]:
        url = r.get("url")
        if not url:
            continue
        print(f"[search] source: {url}")
        results.append({
            "title": scrub_prices(strip_links((r.get("title") or "").strip())),
            "snippet": scrub_prices(strip_links((r.get("content") or "").strip()))[:SNIPPET_CHARS],
        })

    print(f"[search] '{query}' -> {len(results)} result(s)")
    if not results:
        return json.dumps({"ok": True, "query": query, "results": [],
                           "message": "No live results found."})
    return json.dumps({
        "ok": True, "query": query, "results": results,
        "note": ("Research only. Links and prices are intentionally omitted — do "
                 "not mention websites, links or prices. Route the guest to their "
                 "Horizon Voyages advisor."),
    })
