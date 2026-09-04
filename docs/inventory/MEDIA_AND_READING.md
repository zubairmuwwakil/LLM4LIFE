# Media, Entertainment & Reading Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record current entertainment/media platforms and identify where long-term tracking or integration adds value without over-engineering passive consumption.

## Current usage

| System | Current role | Provisional long-term direction |
|---|---|---|
| **YouTube** | Video consumption / discovery | Keep. Treat as a media source, not canonical personal state unless watchlists/history become intentionally modeled |
| **Apple Music** | Primary music service | Keep for now. Good fit with Apple-device ecosystem; no need to change without a specific integration/productivity reason |
| **Netflix** | Streaming video | Keep as a subscription/service; do not architect around it |
| **Disney+** | Streaming video | Keep as a subscription/service; do not architect around it |
| **Prime Video** | Streaming video | Keep as a subscription/service; do not architect around it |
| **PlayStation** | Gaming platform | Keep as entertainment platform; no canonical life-system role needed |
| **Nintendo** | Gaming platform | Keep as entertainment platform; no canonical life-system role needed |
| **Book reading** | Reads books online but does not consistently track titles, progress, ratings, or reading history | Introduce a lightweight reading tracker if the friction remains low and the data can be exported/integrated |

## Reading tracker recommendation

For a long-term, AI-friendly architecture, prefer a reading tracker with:

- reliable export/import;
- a usable API or structured data access;
- low friction for logging books;
- ownership portability so reading history is not trapped in one vendor;
- enough metadata to support future LLM4LIFE recommendations and summaries without making LLM4LIFE itself the primary book catalog.

### Current preferred candidate: Hardcover

Hardcover is the current preferred candidate for evaluation because it provides a documented API and supports modern book tracking, lists, stats, and cross-platform usage. The important architectural benefit is that LLM4LIFE could later consume or synchronize structured reading data through an explicit API rather than relying on scraping or manual duplication.

This is still provisional. StoryGraph may be preferable if the user values richer reading analytics/recommendations more than API-level integration, while a local/private tracker may be preferable if privacy and direct data ownership become the dominant requirement.

## Production-grade direction

Do not centralize streaming histories, gaming data, or media metadata merely because it is technically possible. Only ingest data that has a clear user-facing benefit.

A sensible future reading flow would be:

```text
Reading tracker
     |
     v
structured reading history
     |
     +--> LLM4LIFE recommendations / summaries / goals
     |
     +--> optional Obsidian notes for books worth remembering
```

The reading tracker owns reading-log state; Obsidian owns durable personal notes/insights about books; LLM4LIFE may orchestrate across them.

## Implementation follow-up after inventory

- Evaluate Hardcover vs StoryGraph vs a private/local option based on API/export quality, friction, and privacy.
- If a tracker is adopted, define a minimal schema: book, status, started_at, finished_at, rating, optional notes/tags.
- Avoid duplicating complete book metadata in Neon unless there is a concrete orchestration need; store external IDs/references where possible.
- Consider a simple mobile capture action such as `I started <book>` / `I finished <book>` routed through LLM4LIFE.
