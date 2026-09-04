# Commerce, Lifestyle & Edge Systems Inventory

**Status:** Inventory complete / architecture decisions still revisitable  
**Updated:** 2026-09-02

This file captures the final low-coupling apps and lifestyle systems discovered during the full LLM4LIFE inventory. These are mostly provider/execution surfaces rather than core sources of truth.

## Food delivery

Current providers:

- DoorDash
- Uber Eats
- SkipTheDishes

The user has no platform loyalty and normally chooses whichever option has the best effective price/discount for the order.

**Direction:** keep multiple providers. Do not introduce a canonical food-delivery platform. LLM4LIFE may eventually compare total price, promotions, delivery fees and available rewards when enough supported data is available, but it should not create another paid service merely to do so.

## Banking and card-provider apps

The user uses the official apps associated with the banks/cards/accounts they hold.

**Direction:** provider apps remain authoritative execution/account surfaces. Consolidated user-owned financial state belongs in InUnity. Do not make LLM4LIFE a shadow bank ledger and do not store bank credentials in this repository.

## General shopping

The user has no meaningful retailer loyalty and shops wherever makes sense for the current purchase.

**Direction:** treat stores and marketplaces as interchangeable commerce providers. Future AI assistance should optimize for total value — price, shipping, cashback/rewards, return policy and convenience — instead of forcing a preferred retailer.

## Dating apps

No durable platform preference or canonical dating application was identified.

**Direction:** dating apps, when used, are communication/discovery surfaces only. Relationship context worth intentionally retaining belongs in the private Obsidian People/Relationships system under the privacy rules documented elsewhere.

## Sports

Pickleball is the meaningful recurring sport/activity. The user's own pickleball software/projects are documented separately.

**Direction:** avoid adding another generic sports-tracking platform unless a concrete need appears.

## Weather

The user normally gets weather through Apple's weather experience.

**Direction:** weather is an external context signal, not stored durable state. LLM4LIFE should query current weather when planning/travel/errand decisions actually depend on it rather than persist forecasts.

## Camera / photography

The user owns a Sony Alpha-series full-frame camera believed to be an **a7 IV**. Exact model should be verified before any device-specific automation or accessory decision.

**Direction:** treat the camera as a creative hardware endpoint. Photo-library/storage workflow should be assessed only when there is a demonstrated organization/backup problem; do not invent a DAM workflow merely because a camera exists.

## Architectural pattern

These systems share the same rule:

```text
provider / execution surface
          |
          v
LLM4LIFE may compare, route or contextualize
          |
          v
only durable information with a real future use is written to a canonical domain
```

Do not centralize transaction-by-transaction or activity-by-activity history simply because an API or app exposes it.

## Free-first rule

No new paid subscription should be introduced for these domains unless the value is clearly material and existing/free capabilities cannot reasonably provide it.
