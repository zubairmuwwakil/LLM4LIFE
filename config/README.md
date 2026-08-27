# Machine-Readable Configuration

Files in this directory are concise snapshots that AI agents can parse without reconstructing policy from prose.

## Files

- `tools.yaml` — tool roles, runtime status, actors, access limitations, canonical routing
- `automations.yaml` — active automation set and interaction rules
- `scheduling.yaml` — default scheduling window and planning preferences

## Rules

1. These files describe **current behavior/state**, not full rationale.
2. Human-readable rationale belongs in `docs/`.
3. Do not place credentials, tokens, account IDs, private message content, or sensitive personal data here.
4. A YAML entry saying a tool is canonical does not prove a connector is live; runtime status must be verified.
5. If a live automation is changed, update `automations.yaml` after the actual runtime change succeeds.
6. If a connector/bridge is deployed or removed, update `tools.yaml` and `docs/STATUS.md`.
7. If a scheduling preference changes, update `scheduling.yaml`, `docs/PLANNING.md`, and the live planner automation.
8. Keep values easy for agents to diff and interpret; avoid embedding long prompts or duplicated prose.

See `docs/README.md` for documentation precedence.
