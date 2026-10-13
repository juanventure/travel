/**
 * Horizon Voyages - Digital Itinerary Data Model
 * Sample High-End Curated Voyage
 */
const VOYAGE_DATA = {
  id: "HV-2026-GRE-8821",
  title: "12-Night Greek Isles & Adriatic Luxury Expedition",
  tagline: "Curated Luxury Voyage aboard Celebrity Beyond",
  client: {
    leadGuest: "Eleanor & Marcus Vance",
    partySize: 2,
    celebration: "20th Wedding Anniversary",
    loyaltyTier: "Captain's Club Elite"
  },
  advisor: {
    name: "Juan Garcia",
    agency: "Horizon Voyages (Fora Travel)",
    phone: "+1 (800) 555-0199",
    email: "juan@horizonvoyages.com",
    avatar: "assets/advisor_portrait.png",
    conciergeHours: "24/7 Priority Sea Support"
  },
  booking: {
    cruiseLine: "Celebrity Cruises",
    ship: "Celebrity Beyond (Edge Class)",
    confirmation: "CEL-8392019",
    stateroom: "AquaClass Stateroom #10184 (Deck 10 - Midship)",
    diningSeating: "Blu Exclusive Dining / Flexible Seating",
    embarks: {
      port: "Civitavecchia (Rome), Italy",
      date: "2026-10-24",
      time: "17:00",
      boardingWindow: "12:00 PM – 03:30 PM",
      terminal: "Amerigo Vespucci Cruise Terminal 25"
    },
    disembarks: {
      port: "Civitavecchia (Rome), Italy",
      date: "2026-11-05",
      time: "06:30"
    },
    amenitiesIncluded: [
      "Classic Drinks Package (Upgraded to Premium courtesy of Horizon Voyages)",
      "Stream High-Speed Satellite Wi-Fi (2 Devices)",
      "Daily Prepaid Gratuities",
      "$400 Onboard Spending Credit (OBC)",
      "Complimentary SEA Thermal Suite & Persian Garden Access",
      "Dedicated AquaClass Concierge & Daily Afternoon Savories"
    ]
  },
  countdownTarget: "2026-10-24T12:00:00",
  heroImage: "assets/cruise_mediterranean.png",
  logistics: {
    flights: [
      {
        direction: "Outbound",
        airline: "Delta Air Lines / ITA Airways",
        flightNumber: "DL 148 / AZ 608",
        departure: {
          airport: "JFK (New York)",
          time: "2026-10-22 17:45",
          terminal: "Terminal 4"
        },
        arrival: {
          airport: "FCO (Rome Fiumicino)",
          time: "2026-10-23 08:15 (+1 Day)",
          terminal: "Terminal 3"
        },
        cabin: "Delta One / Business",
        seats: "4A, 4B",
        confirmation: "DL-982WJ4",
        notes: "Horizon Voyages pre-arranged VIP baggage assistance upon arrival at FCO."
      },
      {
        direction: "Inbound Return",
        airline: "Delta Air Lines",
        flightNumber: "DL 149",
        departure: {
          airport: "FCO (Rome Fiumicino)",
          time: "2026-11-05 12:40",
          terminal: "Terminal 3"
        },
        arrival: {
          airport: "JFK (New York)",
          time: "2026-11-05 16:55",
          terminal: "Terminal 4"
        },
        cabin: "Delta One / Business",
        seats: "3A, 3B",
        confirmation: "DL-982WJ4",
        notes: "Post-cruise private express Mercedes van transfer from pier direct to FCO T3."
      }
    ],
    hotel: {
      name: "Hotel de Russie, Rocco Forte",
      location: "Via del Babuino 9, 00187 Rome, Italy",
      checkIn: "2026-10-23 (Early Check-In Requested & Confirmed)",
      checkOut: "2026-10-24 (11:00 AM)",
      roomType: "Executive Suite overlooking Secret Garden",
      confirmation: "RF-827391",
      amenities: [
        "Full Italian Buffet Breakfast for two daily in Le Jardin de Russie",
        "€100 Food & Beverage or Spa Credit",
        "Complimentary bottle of Franciacorta upon arrival",
        "Guaranteed 2:00 PM late check-out on embarkation morning"
      ],
      notes: "Horizon Voyages Advisor VIP welcome note on file with Concierge."
    },
    transfers: [
      {
        date: "2026-10-23",
        time: "09:00 AM",
        service: "Airport to Hotel Private Chauffeur",
        driverDetails: "Driver Luca waiting at FCO Baggage Exit with 'Vance' sign (Mercedes S-Class)."
      },
      {
        date: "2026-10-24",
        time: "11:30 AM",
        service: "Hotel to Ship Embarkation Transfer",
        driverDetails: "Mercedes V-Class from Hotel de Russie lobby direct to Civitavecchia Pier 25."
      },
      {
        date: "2026-11-05",
        time: "08:30 AM",
        service: "Ship to Airport Express Transfer",
        driverDetails: "Pier 25 Luggage Exit direct to Rome Fiumicino (FCO) Terminal 3."
      }
    ]
  },
  days: [
    {
      dayNumber: 1,
      date: "Saturday, Oct 24, 2026",
      type: "Embarkation",
      port: "Civitavecchia (Rome), Italy",
      arrival: "—",
      departure: "17:00 (All Aboard 15:30)",
      weather: "72°F / 22°C • Sunny",
      highlight: "Welcome aboard Celebrity Beyond! AquaClass priority embarkation and welcome champagne in the Grand Plaza.",
      schedule: [
        {
          time: "11:30 AM",
          category: "Transfer",
          title: "Private Chauffeur Pickup",
          desc: "Luggage loaded at Hotel de Russie; scenic 60-minute drive to the port."
        },
        {
          time: "12:45 PM",
          category: "Cruise",
          title: "Priority Terminal Check-In",
          desc: "Proceed through the AquaClass / Suites expedited security lane at Terminal 25."
        },
        {
          time: "01:30 PM",
          category: "Dining",
          title: "Welcome Lunch at The Retreat Lounge or Blu",
          desc: "Relax over a light Mediterranean lunch while the main crowd boards."
        },
        {
          time: "05:00 PM",
          category: "Sailaway",
          title: "Sailaway Toast on The Sunset Bar",
          desc: "Grab signature cocktails designed by Nate Berkus at the aft multi-level terrace."
        },
        {
          time: "08:00 PM",
          category: "Dining",
          title: "Dinner at Blu",
          desc: "Clean-cuisine dining exclusive to AquaClass guests. No reservations needed."
        }
      ],
      dressCode: "Smart Casual",
      tip: "Complete your muster safety drill on the Celebrity mobile app immediately upon entering your suite."
    },
    {
      dayNumber: 2,
      date: "Sunday, Oct 25, 2026",
      type: "Sea Day",
      port: "Cruising the Ionian Sea",
      arrival: "—",
      departure: "—",
      weather: "75°F / 24°C • Gentle Breeze",
      highlight: "Full day of ocean wellness, SEA Thermal Suite thermal loungers, and sunset dining.",
      schedule: [
        {
          time: "09:00 AM",
          category: "Wellness",
          title: "Persian Garden & Crystal Atrium Relaxation",
          desc: "Enjoy the heated marble loungers, salt room, and rainfall aromatherapy showers."
        },
        {
          time: "01:00 PM",
          category: "Dining",
          title: "Lunch at Rooftop Garden Grill",
          desc: "Alfresco dining with panoramic 360-degree sea vistas."
        },
        {
          time: "04:30 PM",
          category: "Activity",
          title: "Magic Carpet Cantilever Experience",
          desc: "Experience cocktails hovering 13 stories above sea level over the starboard edge."
        },
        {
          time: "08:30 PM",
          category: "Dining",
          title: "Anniversary Celebration Dinner at Le Voyage",
          desc: "Confirmed reservation at Chef Daniel Boulud's signature luxury venue. Tasting menu with wine pairings."
        }
      ],
      dressCode: "Evening Chic (Formal / Cocktail)",
      tip: "We've notified the Maître D' at Le Voyage of your 20th anniversary; expect an elevated celebratory touch!"
    },
    {
      dayNumber: 3,
      date: "Monday, Oct 26, 2026",
      type: "Port Call",
      port: "Santorini, Greece",
      arrival: "08:00 AM",
      departure: "19:00 (Tender Last Call 18:00)",
      weather: "74°F / 23°C • Clear & Crisp",
      highlight: "Iconic blue domes, clifftop views in Oia, and an exclusive private catamaran caldera cruise.",
      schedule: [
        {
          time: "08:30 AM",
          category: "Tender",
          title: "Priority Tender Ticket",
          desc: "Present your SeaPass card at Guest Services for immediate first-wave tender boat down to Athinios Port."
        },
        {
          time: "09:30 AM",
          category: "Excursion",
          title: "Curated Private Catamaran & Oia Winery Tour",
          desc: "Private skippered catamaran sailing through the caldera hot springs, followed by VIP wine tasting overlooking the cliffs of Pyrgos. Voucher #SAN-4819."
        },
        {
          time: "04:30 PM",
          category: "Leisure",
          title: "Fira Clifftop Stroll & Shopping",
          desc: "Art galleries, Greek linen boutiques, and iced freddo espressos overlooking the volcano."
        },
        {
          time: "06:00 PM",
          category: "Tender",
          title: "Final Tender Return to Beyond",
          desc: "Board the tender from the Old Port or take the cable car down."
        }
      ],
      dressCode: "Smart Casual",
      tip: "Wear comfortable walking shoes with good grip — Santorini cobblestones are polished and can be slippery."
    },
    {
      dayNumber: 4,
      date: "Tuesday, Oct 27, 2026",
      type: "Port Call",
      port: "Ephesus (Kusadasi), Turkey",
      arrival: "07:30 AM",
      departure: "18:00 (All Aboard 17:30)",
      weather: "71°F / 22°C • Sunny",
      highlight: "Step back 2,000 years into one of antiquity's best-preserved Roman cities and Terrace Houses.",
      schedule: [
        {
          time: "08:15 AM",
          category: "Excursion",
          title: "Private VIP Tour of Ancient Ephesus & Terrace Houses",
          desc: "Expert private archeologist guide meets you pier-side. Exclusive fast-track entry to the Terrace Houses mosaics before large tour buses arrive. Voucher #EPH-9102."
        },
        {
          time: "01:00 PM",
          category: "Dining",
          title: "Authentic Turkish Garden Lunch",
          desc: "Traditional mezze, grilled kebabs, and pomegranate tea under shaded olive groves in Sirince village."
        },
        {
          time: "04:00 PM",
          category: "Shopping",
          title: "Kusadasi Grand Bazaar & Turkish Silk",
          desc: "Stroll along the waterfront promenade right beside the ship."
        }
      ],
      dressCode: "Casual / Sun Hat & Shoulders Covered for Historic Sites",
      tip: "Carry your passport when leaving the ship in Turkey; immigration spot checks are common."
    },
    {
      dayNumber: 5,
      date: "Wednesday, Oct 28, 2026",
      type: "Port Call",
      port: "Mykonos, Greece",
      arrival: "08:00 AM",
      departure: "22:00 (Late Night Stay)",
      weather: "73°F / 23°C • Breezy",
      highlight: "Windmills, whitewashed alleys of Little Venice, and sunset cocktails over the Aegean.",
      schedule: [
        {
          time: "10:00 AM",
          category: "Leisure",
          title: "Morning in Chora (Old Town)",
          desc: "Explore the labyrinth streets before the midday heat. Photo stops at the Kato Mili windmills."
        },
        {
          time: "01:30 PM",
          category: "Dining",
          title: "Beach Club Lunch at Scorpios or Alemagou",
          desc: "Beachfront daybeds, fresh Aegean sea bass, and chilled Assyrtiko wine."
        },
        {
          time: "06:30 PM",
          category: "Cocktails",
          title: "Sunset Aperitivo in Little Venice",
          desc: "Reserved seaside balcony table at Caprice Bar for legendary Aegean sunset hues."
        },
        {
          time: "09:30 PM",
          category: "Cruise",
          title: "Starlit Return to Ship",
          desc: "Late-night departure allows you to experience the island fully lit up at night."
        }
      ],
      dressCode: "Resort Chic",
      tip: "The SeaBus shuttle connects Tourlos cruise pier directly to Chora in 8 minutes for €2 per person."
    },
    {
      dayNumber: 6,
      date: "Thursday, Oct 29, 2026",
      type: "Port Call",
      port: "Athens (Piraeus), Greece",
      arrival: "06:00 AM",
      departure: "18:00 (All Aboard 17:30)",
      weather: "68°F / 20°C • Mild",
      highlight: "The cradle of Western civilization — Acropolis, Parthenon, and the historic Plaka district.",
      schedule: [
        {
          time: "07:30 AM",
          category: "Excursion",
          title: "Early Bird Acropolis & Parthenon VIP Tour",
          desc: "Private Mercedes vehicle to the Acropolis south slope; early access before cruise crowds peak. Voucher #ATH-1120."
        },
        {
          time: "11:30 AM",
          category: "Culture",
          title: "New Acropolis Museum & Plaka Walkway",
          desc: "Glass floors overlooking ancient excavations followed by artisan shopping in Anafiotika."
        },
        {
          time: "01:30 PM",
          category: "Dining",
          title: "Traditional Lunch in Monastiraki",
          desc: "Authentic Greek souvlaki, saganaki, and Greek salad in shaded courtyards."
        }
      ],
      dressCode: "Comfortable Walking Clothes & Sturdy Shoes",
      tip: "Athens traffic back to Piraeus can be heavy in the afternoon; leave the city center by 3:30 PM at latest."
    },
    {
      dayNumber: 7,
      date: "Friday, Oct 30, 2026",
      type: "Sea Day",
      port: "Cruising the Mediterranean",
      arrival: "—",
      departure: "—",
      weather: "72°F / 22°C • Sunny",
      highlight: "Relaxation, pool cabanas, and culinary immersion at the Tuscan Restaurant.",
      schedule: [
        {
          time: "10:00 AM",
          category: "Wellness",
          title: "Morning Yoga on the Resort Deck",
          desc: "Complimentary class with ocean horizon views."
        },
        {
          time: "02:00 PM",
          category: "Culinary",
          title: "Master Sommelier Wine Tasting",
          desc: "Interactive tasting in Cellar Masters showcasing Mediterranean and Super Tuscan vintages."
        },
        {
          time: "07:30 PM",
          category: "Show",
          title: "The Theatre: 'Elements' Aerial & Acrobatics",
          desc: "High-tech immersive theatrical show featuring 110-foot curved LED screens."
        }
      ],
      dressCode: "Smart Casual",
      tip: "Ask the Blu sommelier to open your preferred wine and hold it for you across consecutive dinners."
    },
    {
      dayNumber: 8,
      date: "Saturday, Oct 31, 2026",
      type: "Port Call",
      port: "Valletta, Malta",
      arrival: "08:00 AM",
      departure: "18:00 (All Aboard 17:30)",
      weather: "70°F / 21°C • Bright",
      highlight: "Sail into the Grand Harbour — one of the most cinematic natural harbors in the world.",
      schedule: [
        {
          time: "07:45 AM",
          category: "Sailaway",
          title: "Deck 15 Grand Harbour Arrival Viewing",
          desc: "Be on the top deck or your balcony as the ship enters the towering limestone fortress walls."
        },
        {
          time: "09:30 AM",
          category: "Culture",
          title: "St. John's Co-Cathedral & Caravaggio Masterpieces",
          desc: "Marvel at the marble tombstone floors and Caravaggio's famous 'Beheading of Saint John'."
        },
        {
          time: "01:00 PM",
          category: "Dining",
          title: "Upper Barrakka Gardens Lunch",
          desc: "Panoramic views over the Three Cities with the noon cannon firing ceremony."
        }
      ],
      dressCode: "Smart Casual",
      tip: "The cruise pier in Valletta is right at the base of the city; take the Barrakka panoramic lift directly to town."
    },
    {
      dayNumber: 9,
      date: "Sunday, Nov 01, 2026",
      type: "Port Call",
      port: "Messina (Sicily), Italy",
      arrival: "08:00 AM",
      departure: "18:00 (All Aboard 17:30)",
      weather: "69°F / 21°C • Mild",
      highlight: "Excursion to Taormina, Mount Etna views, and Sicilian cannoli.",
      schedule: [
        {
          time: "08:45 AM",
          category: "Excursion",
          title: "Private Drive to Taormina & Greek Amphitheatre",
          desc: "Drive along the Sicilian coastline to the cliffside town of Taormina with Mount Etna in the backdrop. Voucher #SIC-5091."
        },
        {
          time: "01:00 PM",
          category: "Dining",
          title: "Sicilian Lunch & Fresh Cannoli",
          desc: "Taste fresh ricotta cannoli at Laboratorio Pasticceria Roberto on Via Giardinetti."
        }
      ],
      dressCode: "Casual",
      tip: "Take 10 minutes at noon back in Messina to watch the world's largest astronomical clock chime at the Cathedral."
    },
    {
      dayNumber: 10,
      date: "Monday, Nov 02, 2026",
      type: "Port Call",
      port: "Naples / Amalfi Coast, Italy",
      arrival: "07:00 AM",
      departure: "18:30 (All Aboard 18:00)",
      weather: "67°F / 19°C • Pleasant",
      highlight: "Capri boat charter or scenic private drive down the Amalfi Coast cliff highway.",
      schedule: [
        {
          time: "08:00 AM",
          category: "Excursion",
          title: "Private Capri & Anacapri Hydrofoil Charter",
          desc: "Fast private boat to Marina Grande, convertible taxi up to Anacapri and Villa San Michele. Voucher #CAP-7714."
        },
        {
          time: "01:30 PM",
          category: "Dining",
          title: "Lunch under Lemon Groves at Da Paolino",
          desc: "Dine beneath hanging Sorrento lemon trees. Try the mozzarella in lemon leaves."
        }
      ],
      dressCode: "Smart Resort",
      tip: "If you prefer to stay in Naples, Juan's favorite pizza stop is L'Antica Pizzeria da Michele (10 min taxi from port)."
    },
    {
      dayNumber: 11,
      date: "Tuesday, Nov 03, 2026",
      type: "Port Call",
      port: "Florence / Pisa (Livorno), Italy",
      arrival: "07:00 AM",
      departure: "19:00 (All Aboard 18:30)",
      weather: "65°F / 18°C • Crisp",
      highlight: "Tuscan rolling hills, Chianti vineyards, or the masterpieces of the Uffizi Gallery.",
      schedule: [
        {
          time: "07:30 AM",
          category: "Excursion",
          title: "Private Chauffeur to Florence & Uffizi Priority",
          desc: "Luxury Mercedes sedan straight to Piazza della Signoria. Skip-the-line reservations for Michelangelo's David. Voucher #FLO-3382."
        },
        {
          time: "01:00 PM",
          category: "Dining",
          title: "Tuscan Truffle Lunch at Buca Mario",
          desc: "Bistecca alla Fiorentina and local Brunello di Montalcino in a 16th-century cellar."
        }
      ],
      dressCode: "Smart Casual / Layered for Autumn",
      tip: "Livorno is 75 minutes from Florence. Always budget to depart Florence by 4:00 PM to ensure on-time ship return."
    },
    {
      dayNumber: 12,
      date: "Wednesday, Nov 04, 2026",
      type: "Sea Day",
      port: "Cruising the Tyrrhenian Sea",
      arrival: "—",
      departure: "—",
      weather: "68°F / 20°C • Sunny",
      highlight: "Final relaxing day at sea before arrival in Rome. Luggage collection & farewell dinner.",
      schedule: [
        {
          time: "11:00 AM",
          category: "Leisure",
          title: "Pack & Attach Color-Coded Luggage Tags",
          desc: "Place large bags outside your stateroom door before 10:00 PM tonight for pier delivery tomorrow morning."
        },
        {
          time: "02:00 PM",
          category: "Review",
          title: "Settle Onboard Account",
          desc: "Review your stateroom folio on the TV or app; your $400 OBC has been credited."
        },
        {
          time: "08:00 PM",
          category: "Dining",
          title: "Farewell Dinner at Fine Cut Steakhouse",
          desc: "Dry-aged prime cuts and sunset views celebrating an unforgettable voyage."
        }
      ],
      dressCode: "Smart Casual",
      tip: "Keep a small carry-on bag with passport, medications, and clothes for disembarkation morning."
    },
    {
      dayNumber: 13,
      date: "Thursday, Nov 05, 2026",
      type: "Disembarkation",
      port: "Civitavecchia (Rome), Italy",
      arrival: "06:00 AM",
      departure: "—",
      weather: "66°F / 19°C • Clear",
      highlight: "Disembarkation, private express transfer to Rome Fiumicino Airport (FCO), and flight home.",
      schedule: [
        {
          time: "07:00 AM",
          category: "Dining",
          title: "Final Breakfast at Blu",
          desc: "Express hot breakfast before disembarking."
        },
        {
          time: "08:15 AM",
          category: "Disembark",
          title: "Priority AquaClass Walk-Off",
          desc: "Disembark and collect luggage in baggage hall terminal zone 2."
        },
        {
          time: "08:45 AM",
          category: "Transfer",
          title: "Chauffeur Transfer to FCO Terminal 3",
          desc: "Direct private Mercedes V-Class transfer (approx 45 min drive)."
        },
        {
          time: "12:40 PM",
          category: "Flight",
          title: "Delta Air Lines Flight DL 149 Departs",
          desc: "Delta One / SkyPriority check-in and lounge access."
        }
      ],
      dressCode: "Travel Attire",
      tip: "Juan Garcia will monitor your return flight status and send a welcome-home check-in message."
    }
  ],
  documents: [
    {
      name: "Celebrity SeaPass Xpress Pass",
      status: "Ready for Mobile Wallet",
      type: "Boarding Pass",
      icon: "ticket"
    },
    {
      name: "Allianz Global Assistance Travel Protection",
      policyNumber: "AG-9948210-HV",
      type: "Insurance",
      icon: "shield"
    },
    {
      name: "Private Catamaran & Shore Excursion Vouchers",
      reference: "SAN-4819 & SIC-5091",
      type: "Excursion Vouchers",
      icon: "map-pin"
    },
    {
      name: "Hotel de Russie Confirmation Voucher",
      reference: "RF-827391",
      type: "Hotel Confirmation",
      icon: "home"
    }
  ],
  packingChecklist: [
    "Valid Passports (6+ months validity past Nov 2026)",
    "EU Plug Adapters (Type C/F) & Portable Battery Pack",
    "Formal / Evening Chic attire for 2 gala evenings",
    "Comfortable walking footwear for cobblestones",
    "Light sweater or wrap for Mediterranean sea breezes at night",
    "Prescription medications in original bottles in carry-on"
  ]
};
