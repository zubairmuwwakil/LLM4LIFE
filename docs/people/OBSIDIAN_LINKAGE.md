# People ↔ Obsidian Narrative Linkage

**Phase:** People Phase 4  
**Status:** linkage tooling + localhost bridge implemented; live-vault verification and real mappings pending  
**Privacy rule:** narrative remains in Obsidian; Neon stores only stable identity linkage metadata

## Purpose

Link a stable Neon `person_id` to one or more Obsidian narrative notes without copying note prose, private filenames, contact values, or conversation history into Neon.

This phase may proceed independently of the still-unverified Apple Contacts sync gate. Deferring Apple sync verification does **not** mark that gate passed and does **not** authorize destructive provider cleanup.

The **live local Obsidian vault is authoritative**. The private GitHub Obsidian repository is backup/version history and may be used for read-only discovery, but it is not the preferred write API.

## Link contract

A linked Obsidian note carries two additive managed frontmatter keys:

```yaml
llm4life_person_id: "<stable-neon-person-uuid>"
llm4life_note_id: "<stable-note-uuid>"
```

`llm4life_note_id` is the durable Obsidian-side identity. The note path is intentionally not the cross-system key because notes may be renamed or moved.

Neon reuses the generic `llm4life.external_refs` model:

```text
internal_type = person
internal_id   = <person_id>
system_id     = obsidian
account_scope = <vault scope>
external_id   = note:<llm4life_note_id>
ref_kind      = narrative
metadata      = {"link_contract":"obsidian_frontmatter_v1"}
```

No `person_external_refs` table is introduced. Note paths and narrative text are not stored in Neon.

## Safety invariants

- Never bulk-match Obsidian notes to People by display name alone.
- Linkage requires an explicit private mapping or pre-existing `llm4life_person_id` frontmatter.
- Existing conflicting `llm4life_person_id` values cause an abort rather than overwrite.
- Invalid or conflicting managed note IDs cause an abort.
- Multiple narrative notes may intentionally link to the same person.
- Paths must remain inside the configured vault and hidden paths (including `.obsidian`) are denied.
- Frontmatter edits are additive and atomic.
- Existing unrelated frontmatter and narrative body content are preserved.
- Bridge writes require optimistic concurrency (`expected_sha256`).
- The aggregate receipts contain no person IDs, note IDs, note paths, or narrative.
- The private linkage plan contains only machine linkage IDs required for Neon import; it does not contain narrative or note paths.
- Destructive Obsidian cleanup remains unauthorized.
- V1 of the bridge binds only to `127.0.0.1`; it must not be port-forwarded or publicly exposed as-is.

## Local bridge

The implemented runtime is:

```text
LLM4LIFE local process -> bearer-authenticated localhost adapter -> live Obsidian vault
```

The bridge intentionally exposes only:

```text
GET  /health
GET  /v1/note?path=<relative .md path>       # authenticated read
POST /v1/people/link                         # authenticated managed-frontmatter write only
```

There is no delete, rename, arbitrary file-write, hidden-path, or remote-bind endpoint.

### Configure locally

Copy `.env.example` to a private local environment file or export variables in your shell. At minimum:

```bash
export OBSIDIAN_VAULT_PATH="/absolute/path/to/your/vault"
export OBSIDIAN_VAULT_SCOPE="primary-vault"
export OBSIDIAN_BRIDGE_TOKEN="$(openssl rand -hex 32)"
export OBSIDIAN_ALLOWED_PREFIXES="10 Areas/Relationships"
```

On macOS, multiple allowed prefixes are separated by `:`. Prefer the narrowest practical set. Whole-vault access requires the explicit `OBSIDIAN_BRIDGE_ALLOW_WHOLE_VAULT=true` opt-in and still excludes hidden paths.

Start the bridge:

```bash
bash scripts/run_obsidian_bridge.sh
```

It listens only on `http://127.0.0.1:8765` by default. Audit events are private and content-free at:

```text
.private/obsidian-bridge/audit.jsonl
```

Do **not** commit the token, audit file, manifests, plans, or receipts.

### Verify locally

```bash
curl -s http://127.0.0.1:8765/health
```

Authenticated reads require the bearer token. The read response includes note content because the bridge is the trusted local adapter; the audit log records only a hash of the note path and never records content.

Managed People-link writes require the current note SHA-256 so a concurrent edit cannot be silently overwritten.

## Explicit-link discovery

The discovery helper scans the live vault only for **already explicit** `llm4life_person_id` frontmatter. It does not infer identity from note titles, filenames, backlinks, or prose.

```bash
python3 scripts/people_obsidian_discover.py
```

Default private outputs:

```text
.private/people/obsidian_mapping_manifest.json
.private/people/obsidian_discovery_receipt.json
```

A vault with no explicit People IDs correctly produces zero discovered mappings; that is not a failure and must not be “fixed” with name-only matching.

## Private mapping manifest

For notes that are not already explicitly linked, create a private JSON manifest under `.private/people/`, for example:

```json
{
  "vault_scope": "primary-vault",
  "links": [
    {
      "person_id": "00000000-0000-0000-0000-000000000000",
      "note_path": "Relationships/Example.md"
    }
  ]
}
```

Real IDs and note paths must never be committed to the public repository.

## Plan and apply managed frontmatter

Dry run:

```bash
python3 scripts/people_obsidian_link.py \
  --manifest .private/people/obsidian_person_links.json \
  --vault-root "$OBSIDIAN_VAULT_PATH"
```

Default private outputs:

```text
.private/people/obsidian_external_refs_plan.json
.private/people/obsidian_link_receipt.json
```

After reviewing the private manifest, apply additive frontmatter:

```bash
python3 scripts/people_obsidian_link.py \
  --manifest .private/people/obsidian_person_links.json \
  --vault-root "$OBSIDIAN_VAULT_PATH" \
  --apply-frontmatter
```

The first applied run creates a durable note UUID when absent. Reruns are idempotent.

## Neon import

Install the Phase 4 DB dependency locally:

```bash
python3 -m pip install -r requirements-people-phase4.txt
```

Dry-run the generated private plan against live Neon first:

```bash
python3 scripts/import_people_obsidian_refs.py
```

The importer verifies that every `person_id` exists and is active, refuses an existing note ID owned by another person, rejects metadata beyond the link contract, and writes nothing without `--apply`.

Apply only after the dry run succeeds:

```bash
python3 scripts/import_people_obsidian_refs.py --apply
```

Default private receipt:

```text
.private/people/obsidian_neon_import_receipt.json
```

The only Obsidian-specific value entering Neon is `note:<uuid>` plus the non-sensitive link-contract marker. Narrative and note paths remain outside Neon.

## Remote/cloud access boundary

This bridge is deliberately **not** a public ChatGPT endpoint. Building the localhost adapter does not authorize opening a tunnel, creating credentials, or exposing the vault to the internet.

A later remote-control step must separately choose an authenticated encrypted transport with least-privilege routing. Until then, remote ChatGPT runtimes may use connected backups only for read-only discovery and must not claim direct live-vault access.

## Current completion boundary

Implemented:

- deterministic note identity/frontmatter linker;
- explicit-only discovery;
- localhost-only bearer-authenticated bridge;
- path confinement + hidden-path denial;
- optimistic-concurrency managed frontmatter writes;
- private content-free audit trail;
- dry-run-by-default Neon external-ref importer;
- privacy/safety synthetic tests.

Still requires local/private runtime evidence:

- start bridge against the actual live vault;
- establish explicit private person↔note mappings;
- apply managed frontmatter;
- dry-run and apply validated Neon refs;
- verify aggregate receipts.

Do not weaken identity rules to increase mapping coverage.
