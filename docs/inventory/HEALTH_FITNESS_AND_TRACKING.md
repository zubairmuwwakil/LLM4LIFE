# Health, Fitness & Personal Tracking Inventory

**Status:** Provisional / subject to change  
**Purpose:** Document the health/fitness software architecture without storing private medical details in the public LLM4LIFE repository.

## Current usage

| System | Current role | Provisional long-term direction |
|---|---|---|
| **Apple Health** | Aggregates health and body data, including weight and other device/app contributions | Strong candidate to remain the primary personal health aggregation surface because it is deeply integrated with the user's Apple devices. Do not treat public LLM4LIFE docs as a health-record store |
| **Apple Watch** | Workout tracking and wearable activity capture | Keep as the primary workout/wearable capture device for now; feed supported data into Apple Health |
| **Ultrahuman** | Sleep/recovery tracking and related wearable/app insights | Keep if its data quality and insights continue to provide value; prefer integration into Apple Health where supported rather than maintaining isolated manual records |
| **Google health service** | Used as part of sleep tracking; exact product/app identity should be verified before implementation | Keep provisionally only if it provides unique value. Avoid duplicating the same sleep data across multiple canonical stores |
| **Weight tracking** | Captured through Apple Health | Keep Apple Health as the aggregation surface rather than creating a separate weight database unless a future analytics use case requires normalized backend data |
| **Medication / supplement tracking** | User takes medication and supplements, but no dedicated tracking app was identified in this inventory | Do not store medication names, dosages, or medical history in this public repo. If a future medication-reminder workflow is added, use a private health-capable system and least-privilege integration |

## Production-grade direction

Health data should have a **strict privacy boundary** separate from the public architecture repository.

```text
Apple Watch / Ultrahuman / other health sources
                 |
                 v
            Apple Health
      personal health aggregation
                 |
                 v
       optional private analytics
     only when there is a real need
```

### Principles

1. **Apple Health is the preferred aggregation surface for now**, not LLM4LIFE or Neon by default.
2. **Do not duplicate sensitive health data unnecessarily.** A general-purpose personal orchestration database should not become a shadow medical record.
3. **LLM4LIFE stores architecture, not health content.** It may document integration names, permissions, data classes, and workflows, but not diagnoses, medication names/dosages, lab values, medical records, or other sensitive personal health details.
4. **Use least privilege.** Any future AI access to health data should request only the specific data types needed for a concrete feature.
5. **Prefer projections over copies.** If InUnity/LLM4LIFE eventually needs health context (for example, sleep score or workout completion), prefer narrow derived signals rather than copying the full underlying record.
6. **Avoid false centralization.** Centralizing every data domain in PostgreSQL is not automatically more production-grade; sensitive health data is a domain where specialized platform storage can be the better source of truth.

## Open implementation items

- Verify which Google health product/service is currently involved in sleep tracking.
- Check the actual Apple Health integrations available from Ultrahuman and other active devices/apps before designing sync behavior.
- Decide whether health data ever needs to enter LLM4LIFE's private machine-readable state. Default answer should be **no** unless a specific automation requires it.
- If medication reminders become a desired workflow, evaluate Apple Health/Medications or another privacy-appropriate system rather than putting medication state in the public repo.
