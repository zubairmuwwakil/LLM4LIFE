# Travel, Maps & Mobility Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record the current travel, navigation, transit, ride-hailing and vehicle-related software surfaces for long-term LLM4LIFE architecture design.

## Current usage

| System | Current role | Provisional long-term direction |
|---|---|---|
| **Google Maps** | Primary mapping/navigation/search surface | Keep as a general-purpose navigation and place-discovery client unless a clearly better free alternative emerges |
| **Waze** | Traffic-aware driving/navigation alternative | Keep as a driving-specific client if it continues to provide useful routing/traffic value; avoid duplicating saved-place/state management across both apps where possible |
| **Uber** | Ride-hailing provider | Keep as an execution provider; compare against Lyft on price/availability rather than making either canonical |
| **Lyft** | Ride-hailing provider | Same as Uber; use whichever is cheaper/better for a specific trip |
| **GO Transit** | Regional transit information/service | Keep as an authoritative transit execution/information source for GO-specific service data |
| **PRESTO** | Transit fare/payment/account surface | Keep as the fare/payment execution system; LLM4LIFE should reference relevant trip/payment context rather than replace it |
| **Airline / hotel / booking apps** | No single canonical app in regular use; loyalty/provider-specific usage may exist | Avoid adding a paid travel-planning subscription. Prefer direct provider apps/websites and free planning/integration tools when needed |
| **EV charging apps** | Provider-specific/ad hoc usage for the Bolt EUV; no single canonical app identified in this inventory step | Treat as edge/provider systems. Do not centralize until actual recurring charging providers and integrations are known |
| **Parking apps** | Provider-specific/ad hoc usage; no single canonical app identified | Treat as execution providers only |
| **Toll/transit apps** | Provider-specific/ad hoc usage; no single canonical app identified | Treat as execution providers only |

## Production-grade direction

The travel stack should separate **planning/state** from **execution providers**.

```text
LLM4LIFE / Calendar / trip state
            |
            v
     trip plan / itinerary
            |
   +--------+---------+----------------+
   |                  |                |
 Maps/navigation   transit         ride-hailing
 Google Maps/Waze  GO/PRESTO       Uber/Lyft

 provider-specific airline/hotel/charging/parking/toll systems
 remain execution endpoints
```

### Ownership principles

1. **Navigation apps are clients, not canonical trip databases.** Saved places, itineraries, reminders and trip context should not be trapped in whichever map app was used last.
2. **Ride-hailing should remain competitive.** Do not standardize on Uber or Lyft when the user already benefits from choosing the cheaper/better option per trip.
3. **Transit providers remain authoritative for service/fare execution.** GO Transit and PRESTO own their operational data; LLM4LIFE can surface and coordinate it.
4. **Avoid unnecessary paid travel tooling.** The broader architecture constraint remains free/already-paid-for first.
5. **Provider-specific apps should stay replaceable.** Airline, hotel, charging, parking and toll apps should be treated as external adapters/endpoints rather than architectural dependencies.
6. **CarPlay/iPhone remain priority execution surfaces.** Travel workflows should be safe, glanceable and voice-friendly when used while driving.

## Potential long-term implementation

A future LLM4LIFE travel domain may own only normalized trip metadata such as:

- trip / journey
- origin / destination
- reservation reference
- planned departure / arrival
- transport mode
- provider
- loyalty-program reference
- calendar linkage
- important documents/links
- charging/parking requirement

Do not ingest full location history or mobility data by default. Store only what is useful for planning, reminders, travel coordination or user-requested history.

## Follow-up after inventory

- Decide whether Google Maps alone is sufficient for saved places while Waze remains driving-only.
- Identify any airline/hotel loyalty systems the user actively depends on and whether their apps/API surfaces matter.
- Inventory the actual EV charging providers used with the Bolt before building charging automation.
- Inventory recurring parking/toll providers only if they materially affect workflows.
- Consider a free itinerary/planning layer only if Calendar + LLM4LIFE does not already cover the need.
