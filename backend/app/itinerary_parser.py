"""
AI Cruise Confirmation Parser
Extracts key voyage logistics (cabin numbers, flights, ports, sail dates, amenities)
from unstructured cruise booking emails/PDF text and produces the exact structured
JSON format required by the Horizon Voyages digital itinerary portal.
"""

import os
import re
import json
from datetime import datetime
from typing import Optional

# Import LangChain / Gemini if available
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage
    HAS_LANGCHAIN_GEMINI = True
except ImportError:
    HAS_LANGCHAIN_GEMINI = False


PARSER_SYSTEM_PROMPT = """You are the Senior Cruise Logistics Parser for Horizon Voyages, an ultra-luxury travel advisory affiliated with Fora Travel.
Your task is to ingest unstructured text from a cruise booking confirmation email, invoice, or PDF summary (e.g. Norwegian Cruise Line, Carnival, Celebrity, Royal Caribbean, Princess, Holland America, Virgin Voyages, MSC).

Extract the complete logistics and output ONLY valid, RFC 8259 compliant JSON matching the Horizon Voyages Digital Itinerary schema. Do NOT include markdown code blocks (```json) or commentary. Return purely the raw JSON object.

The target JSON schema structure:
{
  "id": "HV-YYYY-CODE-XXXX",
  "title": "{Duration}-Night {Destination/Region} aboard {Ship}",
  "tagline": "Curated Voyage aboard {Ship}",
  "client": {
    "leadGuest": "Full passenger name(s) or Primary Traveler",
    "partySize": 2,
    "celebration": "Occasion if mentioned (or 'Private Luxury Getaway')",
    "loyaltyTier": "Loyalty status if mentioned (e.g., VIFP Club, Latitudes Rewards, Crown & Anchor, Captain's Club)"
  },
  "advisor": {
    "name": "Juan Garcia",
    "agency": "Horizon Voyages (Fora Travel)",
    "phone": "+1 (800) 555-0199",
    "email": "juan@horizonvoyages.com",
    "avatar": "assets/advisor_portrait.png",
    "conciergeHours": "24/7 Priority Sea Support"
  },
  "booking": {
    "cruiseLine": "e.g. Norwegian Cruise Line, Carnival Cruise Line, Celebrity Cruises",
    "ship": "Full ship name (e.g. Carnival Celebration, Norwegian Prima)",
    "confirmation": "Booking or reservation reference number",
    "stateroom": "Stateroom / Cabin number and category (e.g. Balcony #11204, Havana Suite #8201)",
    "diningSeating": "Dining time or Freestyle / Anytime dining seating details",
    "embarks": {
      "port": "Port of embarkation (City, State/Country)",
      "date": "YYYY-MM-DD",
      "time": "Departure time e.g. 16:00",
      "boardingWindow": "Boarding arrival appointment or check-in window",
      "terminal": "Terminal name/number if specified"
    },
    "disembarks": {
      "port": "Port of disembarkation",
      "date": "YYYY-MM-DD",
      "time": "Arrival/Disembark time e.g. 07:00"
    },
    "amenitiesIncluded": [
      "Extracted included packages, drink packages (Cheers/Free at Sea), Wi-Fi, gratuities, onboard credits (OBC), dining credits"
    ]
  },
  "countdownTarget": "YYYY-MM-DDTHH:MM:SS (embarkation date and start time)",
  "heroImage": "assets/cruise_caribbean.png for Caribbean/Bahamas, assets/cruise_mediterranean.png for Europe/Med, assets/cruise_alaska.png for Alaska, or assets/hero_cruise.png",
  "logistics": {
    "flights": [
      {
        "direction": "Outbound or Return",
        "airline": "Airline name",
        "flightNumber": "Flight number",
        "departure": { "airport": "Airport Code (City)", "time": "YYYY-MM-DD HH:MM", "terminal": "Terminal #" },
        "arrival": { "airport": "Airport Code (City)", "time": "YYYY-MM-DD HH:MM", "terminal": "Terminal #" },
        "cabin": "Class of service",
        "seats": "Seat numbers",
        "confirmation": "Airline PNR / Record Locator",
        "notes": "Transfer or baggage notes"
      }
    ],
    "hotel": {
      "name": "Pre-cruise hotel name",
      "location": "Hotel address",
      "checkIn": "Date",
      "checkOut": "Date",
      "roomType": "Room category",
      "confirmation": "Confirmation number",
      "amenities": ["VIP Perks"],
      "notes": "Advisor concierge notes"
    },
    "transfers": [
      {
        "date": "YYYY-MM-DD",
        "time": "Time",
        "service": "Transfer description (e.g. Airport to Port Private Chauffeur)",
        "driverDetails": "Meeting instructions"
      }
    ]
  },
  "days": [
    {
      "dayNumber": 1,
      "date": "DayOfWeek, Mon DD, YYYY",
      "type": "Embarkation | Port Call | Sea Day | Disembarkation",
      "port": "Port or Sea name",
      "arrival": "Arrival time or '—'",
      "departure": "Departure time with all-aboard",
      "weather": "Realistic destination weather (e.g. 82°F / 28°C • Sunny)",
      "highlight": "Engaging 1-2 sentence destination or day highlight",
      "schedule": [
        { "time": "HH:MM AM/PM", "category": "Transfer | Cruise | Excursion | Dining | Show | Leisure", "title": "Activity Title", "desc": "Detailed event note" }
      ],
      "dressCode": "Casual | Smart Casual | Evening Chic / Formal | White Night",
      "tip": "Advisor insider recommendation for this port or sea day"
    }
  ],
  "documents": [
    { "name": "Digital Boarding Pass", "status": "Ready for Check-In", "type": "Boarding Pass", "icon": "ticket" },
    { "name": "Travel Protection Policy", "policyNumber": "On file with Advisor", "type": "Insurance", "icon": "shield" }
  ],
  "packingChecklist": [
    "Relevant packing items based on cruise line, climate, and itinerary dress codes"
  ]
}

Instructions:
1. If the text does not specify exact flight or hotel details, return empty lists or omit those objects gracefully.
2. Calculate days accurately from embarkation to disembarkation. If port stops are listed, build a full day-by-day object for each day.
3. If specific port arrival/departure times are stated, extract them precisely; otherwise synthesize standard cruise hours (e.g. 08:00 to 17:00).
4. Extract every cabin, deck, and stateroom reference with utmost accuracy.
"""


def _select_hero_image(text: str) -> str:
    """Select best match hero asset based on cruise destination."""
    lower = text.lower()
    if any(k in lower for k in ["alaska", "glacier", "juneau", "skagway", "ketchikan"]):
        return "assets/cruise_alaska.png"
    if any(k in lower for k in ["mediterranean", "greek", "greece", "rome", "italy", "adriatic", "barcelona", "europe"]):
        return "assets/cruise_mediterranean.png"
    if any(k in lower for k in ["caribbean", "bahamas", "nassau", "cozumel", "roatan", "miami", "san juan", "st. thomas"]):
        return "assets/cruise_caribbean.png"
    return "assets/hero_cruise.png"


def _heuristic_fallback_parser(raw_text: str) -> dict:
    """
    Robust deterministic parser when LLM API is unavailable.
    Uses regex to extract cruise lines, reservation numbers, cabin, and ports.
    """
    # Cruise Line & Ship detection
    cruise_lines = {
        "carnival": "Carnival Cruise Line",
        "norwegian": "Norwegian Cruise Line",
        "ncl": "Norwegian Cruise Line",
        "celebrity": "Celebrity Cruises",
        "royal caribbean": "Royal Caribbean",
        "msc": "MSC Cruises",
        "princess": "Princess Cruises",
        "holland america": "Holland America Line",
        "virgin voyages": "Virgin Voyages"
    }

    cruise_line = "Luxury Cruise Line"
    lower_text = raw_text.lower()
    for key, name in cruise_lines.items():
        if key in lower_text:
            cruise_line = name
            break

    # Ship Name extraction
    ship_match = re.search(r"(?:ship|vessel|aboard)\s*[:\-]?\s*([A-Za-z\s]+(?:Celebration|Prima|Beyond|Escape|Encore|Joy|Horizon|Breeze|Vista|Mardi Gras|Wonder of the Seas|Icon of the Seas|Edge|Apex|Ascent))", raw_text, re.IGNORECASE)
    if ship_match:
        ship_name = ship_match.group(1).strip()
    else:
        # Generic ship guess
        ship_words = re.findall(r"(?:Carnival|Norwegian|Celebrity|Royal)\s+([A-Za-z]+)", raw_text, re.IGNORECASE)
        ship_name = f"{cruise_line.split()[0]} {ship_words[0]}" if ship_words else f"{cruise_line} Flagship"

    # Confirmation Code (must be preceded by colon/dash to avoid matching header titles)
    conf_match = re.search(r"(?:confirmation|booking|reservation|record\s*locator|pnr|ref)\s*(?:#|no\.?|code|number|reference|id)?\s*[:\-]\s*([A-Za-z0-9\-]{5,15})", raw_text, re.IGNORECASE)
    confirmation = conf_match.group(1).strip().upper() if conf_match else "HV-PENDING"

    # Stateroom / Cabin
    cabin_match = re.search(r"(?:stateroom|cabin|room)\s*(?:#|no\.?)?\s*[:\-]\s*([^\r\n]+)", raw_text, re.IGNORECASE)
    stateroom_full = cabin_match.group(1).strip() if cabin_match else "Ocean Stateroom"

    # Guest Name
    guest_match = re.search(r"(?:guest(?: name)?|passenger(?: name)?|traveler(?: name)?|primary guest)\s*[:\-]\s*([^\r\n]+)", raw_text, re.IGNORECASE)
    guest_name = guest_match.group(1).strip() if guest_match else "Distinguished Guest"

    # Sail Date
    date_match = re.search(r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+202\d|\d{4}-\d{2}-\d{2})", raw_text)
    sail_date_str = date_match.group(1) if date_match else "2026-11-14"
    try:
        sail_dt = datetime.strptime(sail_date_str.replace(",", ""), "%B %d %Y") if " " in sail_date_str else datetime.strptime(sail_date_str[:10], "%Y-%m-%d")
        sail_iso = sail_dt.strftime("%Y-%m-%d")
    except Exception:
        sail_iso = "2026-11-14"

    # Extract explicitly listed bullet amenities
    amenity_matches = re.findall(r"^[ \t]*[\-\*•]\s*([A-Za-z0-9$][^\r\n]+)", raw_text, re.MULTILINE)
    amenities = [a.strip() for a in amenity_matches if not a.lower().startswith("day ")]
    if not amenities:
        amenities = [
            "Complimentary Stateroom Welcome Touch",
            "Dedicated Horizon Voyages Advisor Support",
            "Pre-Arranged Dining & Port Guidance"
        ]

    # Explicit day line parsing: "Day X - Port (Times)"
    explicit_days = re.findall(r"^[ \t]*Day\s+(\d+)\s*[\-:]\s*([^\r\n]+)", raw_text, re.MULTILINE | re.IGNORECASE)
    days = []

    if explicit_days:
        for num_str, day_desc in explicit_days:
            day_num = int(num_str)
            times_match = re.search(r"\(([^)]+)\)", day_desc)
            time_info = times_match.group(1).strip() if times_match else ""
            port_name = re.sub(r"\(.*?\)", "", day_desc).strip()

            if day_num == 1:
                d_type = "Embarkation"
                arr = "—"
                dep = time_info if "depart" in time_info.lower() else "16:00 (All Aboard 15:00)"
                sched = [
                    {"time": "12:00 PM", "category": "Cruise", "title": "Priority Pier Check-In", "desc": "Proceed to designated terminal security."},
                    {"time": "04:00 PM", "category": "Sailaway", "title": "Sailaway Toast on Top Deck", "desc": "Enjoy departure views as the voyage begins."},
                    {"time": "07:30 PM", "category": "Dining", "title": "Welcome Dinner", "desc": "Main dining room dinner seating."}
                ]
            elif day_num == len(explicit_days):
                d_type = "Disembarkation"
                arr = time_info if "arrive" in time_info.lower() else "07:00 AM"
                dep = "—"
                sched = [
                    {"time": "07:00 AM", "category": "Dining", "title": "Farewell Breakfast", "desc": "Express dining before departure."},
                    {"time": "08:30 AM", "category": "Transfer", "title": "Disembarkation & Transfers", "desc": "Collect luggage and proceed to ground transportation."}
                ]
            else:
                is_sea = "sea" in port_name.lower() or "cruising" in port_name.lower()
                d_type = "Sea Day" if is_sea else "Port Call"
                arr = time_info.split("-")[0].strip() if "-" in time_info else ("—" if is_sea else "08:00 AM")
                dep = time_info.split("-")[-1].strip() if "-" in time_info else ("—" if is_sea else "17:00 (All Aboard 16:30)")
                sched = [
                    {"time": "09:00 AM", "category": "Wellness" if is_sea else "Excursion", "title": f"Explore {port_name}", "desc": "Curated morning activities and shore excursions."},
                    {"time": "01:00 PM", "category": "Dining", "title": "Lunch", "desc": "Poolside casual or specialty venue lunch."},
                    {"time": "08:00 PM", "category": "Show", "title": "Evening Entertainment", "desc": "Main theater theatrical performance."}
                ]

            days.append({
                "dayNumber": day_num,
                "date": f"Day {day_num}",
                "type": d_type,
                "port": port_name,
                "arrival": arr,
                "departure": dep,
                "weather": "78°F / 25°C • Sunny",
                "highlight": f"Experience the beauty of {port_name} with Horizon Voyages VIP coordination.",
                "schedule": sched,
                "dressCode": "Smart Casual" if day_num % 2 == 1 else "Evening Chic / Formal",
                "tip": "Keep room key and ID handy when disembarking for shore calls."
            })
    else:
        # Fallback to ports detection
        ports_found = re.findall(r"(?:Miami|Port Canaveral|Civitavecchia|Rome|Nassau|Cozumel|Costa Maya|Roatan|San Juan|St\. Thomas|Santorini|Mykonos|Athens|Seattle|Juneau|Skagway|Ketchikan)", raw_text, re.IGNORECASE)
        ports_unique = list(dict.fromkeys([p.title() for p in ports_found])) or ["Miami, FL", "Nassau, Bahamas", "At Sea", "Miami, FL"]
        num_days = max(len(ports_unique), 5)
        for i in range(1, num_days + 1):
            if i == 1:
                p = ports_unique[0] if ports_unique else "Miami, FL"
                d_type = "Embarkation"
                arr = "—"
                dep = "16:00 (All Aboard 15:00)"
                sched = [
                    {"time": "12:00 PM", "category": "Cruise", "title": "Priority Pier Check-In", "desc": "Proceed to designated terminal security."},
                    {"time": "04:00 PM", "category": "Sailaway", "title": "Sailaway Celebration", "desc": "Enjoy panoramic top deck departure views."},
                    {"time": "07:30 PM", "category": "Dining", "title": "Welcome Dinner", "desc": "Main dining room dinner seating."}
                ]
            elif i == num_days:
                p = ports_unique[0] if ports_unique else "Miami, FL"
                d_type = "Disembarkation"
                arr = "07:00 AM"
                dep = "—"
                sched = [
                    {"time": "07:00 AM", "category": "Dining", "title": "Farewell Breakfast", "desc": "Express dining before departure."},
                    {"time": "08:30 AM", "category": "Transfer", "title": "Disembarkation & Transfers", "desc": "Collect luggage and proceed to ground transportation."}
                ]
            else:
                p = ports_unique[min(i - 1, len(ports_unique) - 1)] if len(ports_unique) > 1 else "Cruising at Sea"
                d_type = "Port Call" if "Sea" not in p else "Sea Day"
                arr = "08:00 AM" if d_type == "Port Call" else "—"
                dep = "17:00 (All Aboard 16:30)" if d_type == "Port Call" else "—"
                sched = [
                    {"time": "09:00 AM", "category": "Excursion" if d_type == "Port Call" else "Wellness", "title": f"Explore {p}", "desc": "Curated morning activities and shore excursions."},
                    {"time": "01:00 PM", "category": "Dining", "title": "Lunch", "desc": "Poolside casual or specialty venue lunch."},
                    {"time": "08:00 PM", "category": "Show", "title": "Evening Entertainment", "desc": "Main theater theatrical performance."}
                ]

            days.append({
                "dayNumber": i,
                "date": f"Day {i}",
                "type": d_type,
                "port": p,
                "arrival": arr,
                "departure": dep,
                "weather": "78°F / 25°C • Sunny",
                "highlight": f"Experience the best of {p} with Horizon Voyages VIP coordination.",
                "schedule": sched,
                "dressCode": "Smart Casual" if i % 2 == 1 else "Evening Chic / Formal",
                "tip": "Keep room key and ID handy when disembarking for shore calls."
            })

    hero_img = _select_hero_image(raw_text)
    total_days = len(days) if days else 7
    nights = max(total_days - 1, 1)

    return {
        "id": f"HV-{sail_iso[:4]}-{confirmation[:6]}",
        "title": f"{nights}-Night Voyage aboard {ship_name}",
        "tagline": f"Curated Luxury Voyage aboard {ship_name}",
        "client": {
            "leadGuest": guest_name,
            "partySize": 2,
            "celebration": "Private Luxury Getaway",
            "loyaltyTier": "VIP Guest"
        },
        "advisor": {
            "name": "Juan Garcia",
            "agency": "Horizon Voyages (Fora Travel)",
            "phone": "+1 (800) 555-0199",
            "email": "juan@horizonvoyages.com",
            "avatar": "assets/advisor_portrait.png",
            "conciergeHours": "24/7 Priority Sea Support"
        },
        "booking": {
            "cruiseLine": cruise_line,
            "ship": ship_name,
            "confirmation": confirmation,
            "stateroom": stateroom_full,
            "diningSeating": "Flexible Anytime Dining",
            "embarks": {
                "port": days[0]["port"],
                "date": sail_iso,
                "time": "16:00",
                "boardingWindow": "11:30 AM – 02:30 PM",
                "terminal": "Terminal Port Check-In"
            },
            "disembarks": {
                "port": days[-1]["port"],
                "date": sail_iso,
                "time": "07:00 AM"
            },
            "amenitiesIncluded": [
                "Complimentary Stateroom Welcome Touch",
                "Dedicated Horizon Voyages Advisor Support",
                "Pre-Arranged Dining & Port Guidance"
            ]
        },
        "countdownTarget": f"{sail_iso}T12:00:00",
        "heroImage": hero_img,
        "logistics": {
            "flights": [],
            "hotel": None,
            "transfers": []
        },
        "days": days,
        "documents": [
            {
                "name": f"{cruise_line} Boarding Pass",
                "status": "Check-In Confirmed",
                "type": "Boarding Pass",
                "icon": "ticket"
            },
            {
                "name": "Horizon Voyages Concierge Contact",
                "status": "Active 24/7",
                "type": "Support",
                "icon": "shield"
            }
        ],
        "packingChecklist": [
            "Valid Government ID & Passport",
            "Evening Smart Casual Attire",
            "Comfortable Walking Shoes for Excursions",
            "Sunscreen & Swimwear"
        ]
    }


async def parse_confirmation_text(raw_text: str) -> dict:
    """
    Main parser entrypoint. Uses Gemini 2.5 Flash via LangChain if API key is
    configured, otherwise gracefully executes the deterministic regex parser.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Confirmation text cannot be empty.")

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if HAS_LANGCHAIN_GEMINI and api_key and api_key != "your-gemini-api-key-here":
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.1,
                google_api_key=api_key
            )
            messages = [
                SystemMessage(content=PARSER_SYSTEM_PROMPT),
                HumanMessage(content=f"Please parse this cruise booking confirmation:\n\n{raw_text}")
            ]
            response = await llm.ainvoke(messages)
            content = response.content.strip()

            # Clean potential markdown wrapping
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            parsed_data = json.loads(content)
            # Ensure heroImage is valid asset path
            if not parsed_data.get("heroImage") or not parsed_data["heroImage"].startswith("assets/"):
                parsed_data["heroImage"] = _select_hero_image(raw_text)

            return parsed_data
        except Exception as exc:
            print(f"[itinerary_parser] LLM parsing encountered exception: {exc!r}. Using heuristic fallback.")

    # Fallback parser
    return _heuristic_fallback_parser(raw_text)
