# Devices & Hardware Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record the hardware surfaces LLM4LIFE may need to support, automate, or treat as primary/secondary endpoints. This is architecture inventory, not an asset register; do not store serial numbers, IMEIs, MAC addresses, recovery keys, or other sensitive device identifiers here.

## Current devices

| Device | Current role | Provisional architecture direction |
|---|---|---|
| **2021 MacBook Pro 16-inch (M1 Pro)** | Primary Mac / development machine | Treat as the primary trusted desktop/development endpoint for LLM4LIFE and ORC workflows |
| **2017 MacBook Pro** | Secondary/legacy Mac | Keep as a secondary endpoint for now. There is prior context about an OS/update-related limitation or workaround, but the exact detail was not reliably recovered during this inventory session; verify before designing around it |
| **iPhone 14 Pro** | Primary phone | Treat as the primary mobile control/capture endpoint; prioritize Shortcuts, Share Sheet, notifications, Wallet, messaging, and CarPlay workflows here |
| **iPhone 11 Pro Max** | Secondary phone | Treat as a backup/secondary mobile endpoint; avoid creating workflows that require maintaining duplicate state on both phones |
| **iPad Pro 12.9-inch (approximately 2019-era; exact model/year to verify)** | Tablet / secondary interface | Useful as an additional reading/dashboard/control surface; do not make it a required infrastructure dependency |
| **Apple Watch Series 6** | Wearable | Potential notification, health, quick-action, and context surface; integration value should be evaluated rather than assumed |
| **Google Home devices** | Smart-home / voice-control devices | Treat as edge devices. Preserve only integrations that provide meaningful automation or context; avoid making Google Home itself canonical state |
| **Amazon Alexa devices** | Smart-home / voice-control devices | Same role as Google Home; evaluate overlap and whether maintaining both ecosystems has enough value |
| **2023 Chevrolet Bolt EUV Premier** | Vehicle / CarPlay endpoint | Treat CarPlay as an important mobile execution surface for navigation, safe voice interaction, reminders, and context-aware workflows where supported |
| **External hard drive** | Time Machine backup | Keep. This is a recovery/backup layer, not a synchronization or canonical-storage layer |

## Primary endpoint hierarchy

```text
Primary desktop/development endpoint
    2021 MacBook Pro 16-inch

Primary mobile endpoint
    iPhone 14 Pro

Secondary / fallback endpoints
    2017 MacBook Pro
    iPhone 11 Pro Max
    iPad Pro
    Apple Watch

Ambient / edge endpoints
    CarPlay / Bolt EUV
    Google Home
    Alexa
```

## Production-grade direction

LLM4LIFE should avoid binding core state to any one physical device. Canonical state should live in the appropriate cloud/service/backend systems, while devices act as clients, sensors, capture surfaces, and notification/execution endpoints.

Important principles:

1. **Primary + fallback, not duplicated truth.** The iPhone 14 Pro and 2021 MacBook Pro are primary interfaces. Secondary devices should not require separate manual state maintenance.
2. **Mobile-first ingress matters.** Shortcuts, Share Sheet, notifications, messaging, Wallet, location/context, and CarPlay are high-value inputs/outputs.
3. **Local-only capabilities require bridges.** iMessage, certain Apple integrations, local files, and device automation may require a trusted Mac/iPhone bridge rather than assuming a public API exists.
4. **Smart-home ecosystems are edge integrations.** Google Home and Alexa should be retained only for useful capabilities, not because both happen to exist.
5. **Backups are distinct from sync.** Time Machine remains part of disaster recovery even if cloud storage is centralized elsewhere.
6. **Do not design around the 2017 Mac until its update/support situation is verified.** Its exact prior update-related issue remains an unresolved inventory detail.

## Implementation follow-up after inventory

- Verify the exact 2017 MacBook Pro update/support situation before assigning it an infrastructure role.
- Verify the exact iPad Pro model/year.
- Decide whether the secondary iPhone has a defined operational purpose beyond backup.
- Audit Google Home vs Alexa overlap and determine whether both ecosystems provide enough value to keep integrated.
- Identify Apple-only workflows that require a trusted local bridge and decide whether the primary Mac should host that bridge.
- Treat CarPlay/iPhone as a priority UX surface when designing safe, low-friction mobile automations.
