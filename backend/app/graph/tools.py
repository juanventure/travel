from typing import Optional
from langchain_core.tools import tool

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
    Searches the Global Distribution System (GDS) for available cruise voyages.
    Args:
        region: The destination region (e.g., 'Caribbean', 'Mediterranean', 'Alaska').
        max_price: The maximum budget per person.
    Returns:
        A string formatted list of available voyages.
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
        output += f"- [{v['id']}] {v['nights']} nights in {v['region']} on {v['cruise_line']} {v['ship']} for ${v['price_per_person']}pp (Date: {v['date']})\n"
        
    return output

def get_cruise_details(cruise_id: str) -> Optional[str]:
    """Format a one-line summary of a cruise from the mock GDS, or None if unknown."""
    cruise = next((v for v in MOCK_GDS if v["id"].lower() == cruise_id.lower()), None)
    if not cruise:
        return None
    return (f"- [{cruise['id']}] {cruise['nights']} nights in {cruise['region']} "
            f"on {cruise['cruise_line']} {cruise['ship']} for "
            f"${cruise['price_per_person']}pp (Date: {cruise['date']})")


@tool
def submit_booking_lead(full_name: str, email: str, cruise_id: str) -> str:
    """
    Records a finalized booking lead in the travel agency CRM.
    MUST be called when the user has provided their name, email, and selected a cruise.
    """
    # Records the lead. The agency is notified by email in the booking node so the
    # (blocking) send runs off the event loop and the confirmation can reflect it.
    print(f"*** NEW BOOKING LEAD: {full_name} ({email}) wants to book {cruise_id} ***")
    return f"Booking lead for {full_name} ({email}) on {cruise_id} has been recorded."
