# Browsers & Extensions Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record current browser tooling and evaluate it against long-term LLM4LIFE needs. Every tool here is replaceable if a safer, more scalable, better-integrated alternative exists.

## Current browser

| Tool | Current use | Provisional direction |
|---|---|---|
| **Google Chrome** | Primary browser | Keep for now. Re-evaluate against long-term requirements such as extension support, AI integration, profile isolation, automation, privacy, and cross-device reliability |
| **Ask Gemini / Gemini browser integration** | High-value contextual AI assistance while browsing; particularly useful because the user already has Gemini AI Pro | Keep as a valued capability. Do not bind the architecture to Chrome solely for this feature if an equivalent or better integration becomes available elsewhere |

## Current extensions

| Extension / capability | Current use | Provisional direction |
|---|---|---|
| **MetaMask** | Crypto wallet / Web3 interaction | Keep only in a hardened crypto-specific browser profile or isolated browser environment. Never mix wallet trust with arbitrary browsing/automation if avoidable |
| **Phantom** | Crypto wallet / Web3 interaction | Same rule as MetaMask: isolate from general browsing and AI-driven browser automation |
| **Rakuten** | Cashback / purchase optimization | Keep if useful. Long-term LLM4LIFE/PickMe may eventually ingest cashback opportunities directly so the browser extension becomes one input rather than the only detection mechanism |
| **Ad blocker** | Reduces ads/tracking and improves browsing experience | Keep some form of content/tracker blocking; exact extension/product can be reconsidered based on security, maintenance, and browser support |
| **Teleparty** | Synchronized remote video watching | Keep as a specialized convenience tool if used; no architectural role in LLM4LIFE |
| **Video Speed Controller** | Playback-speed control for online video | Keep if useful; specialized convenience tool with no need to centralize |

## Production-grade browser direction

The browser should be treated as an **execution and capture surface**, not canonical state.

Long-term browser goals:

1. **Profile isolation.** Separate high-risk/high-value contexts from normal browsing.
   - general/personal browsing
   - development/admin
   - crypto/wallet activity
   - optionally AI-agent/browser automation
2. **Least privilege for extensions.** Remove extensions that do not provide enough ongoing value for the permissions they require.
3. **AI-aware browsing without vendor lock-in.** Preserve high-value contextual AI features such as Ask Gemini, while allowing LLM4LIFE to invoke different models/tools when appropriate.
4. **Browser capture should feed canonical systems.** Useful pages/ideas should route through Share Sheet/browser capture/LLM4LIFE into Obsidian, tasks, Notion/Postgres, Jira, etc., instead of disappearing into tabs or bookmarks.
5. **Keep crypto isolated from autonomous agents.** LLM4LIFE browser automation should not have wallet-signing authority by default. Signing/asset movement remains explicitly human-authorized.
6. **Re-evaluate Chrome rather than assuming it wins permanently.** During implementation, compare Chrome against viable long-term alternatives using integration/API/automation support, security, extension ecosystem, AI capabilities, profile isolation, privacy, cross-device support, and operational reliability.

## Provisional profile model

```text
Chrome / chosen primary browser
|
+-- Personal / general
|    +-- Ask Gemini
|    +-- Rakuten
|    +-- content blocking
|    +-- Video Speed Controller / Teleparty
|
+-- Development / admin
|    +-- GitHub / cloud consoles / tooling
|    +-- separate auth/session boundary where practical
|
+-- Crypto
     +-- MetaMask
     +-- Phantom
     +-- no autonomous AI signing
     +-- minimal extensions
```

This is directional and can change after a broader browser/security review.
