# People ↔ Obsidian Narrative Linkage

**Phase:** People Phase 4  
**Status:** linkage tooling ready; live-vault mappings not yet imported  
**Privacy rule:** narrative remains in Obsidian; Neon stores only stable identity linkage metadata

## Purpose

Link a stable Neon `person_id` to one or more Obsidian narrative notes without copying note prose, private filenames, contact values, or conversation history into Neon.

This phase may proceed independently of the still-unverified Apple Contacts sync gate. Deferring Apple sync verification does **not** mark that gate passed and does **not** authorize destructive provider cleanup.

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
```

No `person_external_refs` table is introduced.

## Safety invariants

- Never bulk-match Obsidian notes to People by display name alone.
- Linkage requires an explicit private manifest containing both `person_id` and note path.
- Existing conflicting `llm4life_person_id` values cause an abort rather than overwrite.
- Invalid or duplicate managed note IDs cause an abort.
- Paths must remain inside the configured vault.
- Frontmatter edits are additive and atomic.
- Existing unrelated frontmatter and narrative body content are preserved.
- The aggregate receipt contains no person IDs, note IDs, note paths, or narrative.
- The private linkage plan contains only machine linkage IDs required for a later Neon external-ref import; it does not contain narrative or note paths.
- Destructive Obsidian cleanup remains unauthorized.

## Private manifest

Create a private JSON manifest under `.private/people/`, for example:

```json
{
  "vault_scope": "primary",
  "links": [
    {
      "person_id": "00000000-0000-0000-0000-000000000000",
      "note_path": "Relationships/Example.md"
    }
  ]
}
```

Real IDs and note paths must never be committed to the public repository.

## Dry run

```bash
python3 scripts/people_obsidian_link.py \
  --manifest .private/people/obsidian_person_links.json \
  --vault-root "$OBSIDIAN_VAULT_PATH"
```

This validates the mapping and writes private outputs without modifying notes.

Default private outputs:

```text
.private/people/obsidian_external_refs_plan.json
.private/people/obsidian_link_receipt.json
```

## Apply managed frontmatter

After reviewing the private manifest:

```bash
python3 scripts/people_obsidian_link.py \
  --manifest .private/people/obsidian_person_links.json \
  --vault-root "$OBSIDIAN_VAULT_PATH" \
  --apply-frontmatter
```

The first applied run creates a durable note UUID when absent. Reruns are idempotent.

## Neon import boundary

The generated private plan is intentionally separate from database mutation. A later importer/bridge should:

1. validate every `internal_id` exists as a live `llm4life.people.id`;
2. validate an existing Obsidian `external_id` never points to a different person;
3. upsert only same-identity refs idempotently;
4. write an aggregate action receipt;
5. never copy note prose or note paths into Neon.

Do not weaken these checks to automate ambiguous mappings.

## Live-vault bridge

The long-term runtime remains:

```text
LLM4LIFE -> authenticated least-privilege local adapter -> live Obsidian vault
```

The local vault is the authoritative working copy. A Git backup is not the preferred application write API.
